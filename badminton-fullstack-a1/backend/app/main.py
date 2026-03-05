import os
import threading
import math
import shutil
from pathlib import Path
from typing import List, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import orjson
from .schemas import (
    CreateJobResponse,
    JobStatusResponse,
    RunInfoResponse,
    RunSummaryResponse,
    AnalyticsResponse,
    DeleteRunResponse,
    DeleteAllRunsResponse,
)
from .db import DB
from .paths import runs_root, db_path
from .storage import new_id, ensure_run_dirs, write_json, read_json
from .queue import get_queue

db = DB(db_path())
app = FastAPI(title="Badminton A1 Fullstack API")

def _cors_origins():
    v = os.getenv("FRONTEND_ORIGINS") or os.getenv("FRONTEND_ORIGIN")
    if v:
        parts = [x.strip() for x in v.split(",") if x.strip()]
        if parts:
            return parts
    return [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_dir_of(run_id: str) -> Path:
    return runs_root() / run_id

def _safe_run_dir(run_id: str) -> Path:
    root = runs_root().resolve()
    p = (root / run_id).resolve()
    if p == root or root not in p.parents:
        raise HTTPException(status_code=400, detail="invalid run_id")
    return p

def _load_json(p: Path):
    try:
        return orjson.loads(p.read_bytes())
    except Exception:
        return {}

def _find_any_key(d: dict, keys: list[str]):
    for k in keys:
        if k in d:
            return d[k]
    for k in keys:
        lk = k.lower()
        for kk in d.keys():
            if isinstance(kk, str) and kk.lower() == lk:
                return d[kk]
    return None

def _read_shuttle_csv(csv_path: Path, max_points: int = 12000):
    xs = []
    ys = []
    ts = []
    frames = []
    vis = []
    if not csv_path.exists():
        return xs, ys, ts, frames, vis
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        import csv as _csv
        reader = _csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append(r)
    if not rows:
        return xs, ys, ts, frames, vis
    step = max(1, math.ceil(len(rows) / max_points))
    for i in range(0, len(rows), step):
        r = rows[i]
        fr = _find_any_key(r, ["Frame", "frame", "frames"])
        x = _find_any_key(r, ["X", "x"])
        y = _find_any_key(r, ["Y", "y"])
        v = _find_any_key(r, ["Visibility", "visibility", "vis", "v"])
        try:
            fr_i = int(float(fr))
        except Exception:
            continue
        try:
            x_f = float(x)
        except Exception:
            x_f = None
        try:
            y_f = float(y)
        except Exception:
            y_f = None
        try:
            v_i = int(float(v))
        except Exception:
            v_i = 0
        frames.append(fr_i)
        xs.append(x_f)
        ys.append(y_f)
        vis.append(v_i)
    return xs, ys, ts, frames, vis

def _events_to_times(events_obj: Any, fps: float):
    if isinstance(events_obj, dict):
        if isinstance(events_obj.get("events"), list):
            events_obj = events_obj.get("events")
        elif isinstance(events_obj.get("data"), list):
            events_obj = events_obj.get("data")
        else:
            return []
    if not isinstance(events_obj, list):
        return []
    times = []
    for e in events_obj:
        if not isinstance(e, dict):
            continue
        t = _find_any_key(e, ["t", "time", "sec", "time_sec", "timestamp"])
        fr = _find_any_key(e, ["frame", "Frame", "frm"])
        if t is not None:
            try:
                times.append(float(t))
                continue
            except Exception:
                pass
        if fr is not None and fps > 0:
            try:
                times.append(float(fr) / float(fps))
            except Exception:
                pass
    times = [x for x in times if isinstance(x, (int, float)) and x == x and x >= 0]
    return sorted(times)

def _hits_per_second(times: list[float]):
    if not times:
        return [], []
    mx = int(math.floor(max(times)))
    counts = [0] * (mx + 1)
    for t in times:
        k = int(math.floor(t))
        if 0 <= k < len(counts):
            counts[k] += 1
    xs = list(range(len(counts)))
    ys = counts
    return xs, ys

def _trajectory_series(xs, ys, frames, vis, fps: float):
    if not frames:
        return {"x": [], "y": [], "t": [], "frame": []}
    out_x = []
    out_y = []
    out_t = []
    out_f = []
    last_f = None
    for x, y, f, v in zip(xs, ys, frames, vis):
        gap = 0 if last_f is None else (f - last_f)
        brk = (v == 0) or (last_f is not None and gap > 2) or (x is None) or (y is None)
        if brk and out_f:
            out_x.append(None)
            out_y.append(None)
            out_t.append(None)
            out_f.append(None)
        out_x.append(x)
        out_y.append(y)
        out_t.append(float(f) / float(fps) if fps > 0 else None)
        out_f.append(f)
        last_f = f
    return {"x": out_x, "y": out_y, "t": out_t, "frame": out_f}

@app.post("/jobs", response_model=CreateJobResponse)
async def create_job(video: UploadFile = File(...), params: str = Form(default="{}")):
    try:
        p = orjson.loads(params.encode("utf-8"))
        if not isinstance(p, dict):
            p = {}
    except Exception:
        p = {}

    run_id = new_id("run")
    job_id = new_id("job")

    run_dir = run_dir_of(run_id)
    ensure_run_dirs(run_dir)

    input_path = run_dir / "input" / "upload.mp4"
    with input_path.open("wb") as f:
        while True:
            chunk = await video.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    write_json(run_dir / "params.json", p)
    db.create_job(job_id, run_id)

    if os.getenv("RQ_SYNC", "0") == "1":
        import worker_tasks
        t = threading.Thread(target=worker_tasks.run_job, args=(job_id, run_id, str(input_path), p), daemon=True)
        t.start()
        return CreateJobResponse(job_id=job_id, run_id=run_id)

    q = get_queue()
    q.enqueue("worker_tasks.run_job", job_id, run_id, str(input_path), p, job_id=job_id)
    return CreateJobResponse(job_id=job_id, run_id=run_id)

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str):
    j = db.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(**j)

@app.get("/runs", response_model=List[RunSummaryResponse])
def list_runs(limit: int = Query(default=50, ge=1, le=500)):
    xs = db.list_runs(limit=limit)
    return [RunSummaryResponse(**x) for x in xs]

@app.get("/runs/{run_id}", response_model=RunInfoResponse)
def get_run(run_id: str):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")
    params = orjson.loads(r["params_json"].encode("utf-8"))
    artifacts = orjson.loads(r["artifacts_json"].encode("utf-8"))
    metrics = orjson.loads(r["metrics_json"].encode("utf-8"))
    return RunInfoResponse(
        run_id=r["run_id"],
        status=r["status"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        artifacts=artifacts,
        metrics=metrics,
        params=params,
    )

@app.get("/runs/{run_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(run_id: str):
    run_dir = run_dir_of(run_id)
    manifest = run_dir / "manifest.json"
    if not manifest.exists():
        raise HTTPException(status_code=404, detail="manifest not found")
    m = read_json(manifest)
    artifacts = m.get("artifacts", {})

    fps = 30.0
    vj_rel = artifacts.get("video_json", None)
    if isinstance(vj_rel, str):
        vj = run_dir / vj_rel
        if vj.exists():
            vjo = _load_json(vj)
            try:
                fps = float(vjo.get("fps", fps))
            except Exception:
                fps = 30.0

    shuttle_rel = artifacts.get("shuttle_csv", None)
    shuttle_path = (run_dir / shuttle_rel) if isinstance(shuttle_rel, str) else None
    xs, ys, ts0, frames, vis = _read_shuttle_csv(shuttle_path, max_points=16000) if shuttle_path else ([], [], [], [], [])
    traj = _trajectory_series(xs, ys, frames, vis, fps)

    events_times = []
    ej_rel = artifacts.get("events_json", None)
    if isinstance(ej_rel, str):
        ej = run_dir / ej_rel
        if ej.exists():
            ej_obj = _load_json(ej)
            events_times = _events_to_times(ej_obj, fps)
    x_bins, y_counts = _hits_per_second(events_times)

    return AnalyticsResponse(
        run_id=run_id,
        fps=fps,
        trajectory=traj,
        timeline={"x": x_bins, "y": y_counts},
        meta={"n_points": len([x for x in traj["x"] if x is not None]), "n_events": len(events_times)},
    )

@app.get("/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str):
    run_dir = run_dir_of(run_id)
    manifest = run_dir / "manifest.json"
    if not manifest.exists():
        raise HTTPException(status_code=404, detail="manifest not found")
    m = read_json(manifest)
    artifacts = m.get("artifacts", {})
    if name not in artifacts:
        raise HTTPException(status_code=404, detail="artifact not found")
    rel = artifacts[name]
    p = run_dir / rel
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing")
    media = "application/octet-stream"
    if p.suffix.lower() == ".mp4":
        media = "video/mp4"
    if p.suffix.lower() == ".csv":
        media = "text/csv"
    if p.suffix.lower() == ".json":
        media = "application/json"
    if p.suffix.lower() == ".png":
        media = "image/png"
    return FileResponse(str(p), media_type=media, filename=p.name)

@app.get("/runs/{run_id}/logs")
def get_logs(run_id: str):
    run_dir = run_dir_of(run_id)
    p = run_dir / "logs.txt"
    if not p.exists():
        return {"text": ""}
    return {"text": p.read_text(encoding="utf-8", errors="ignore")[-20000:]}

def _is_active_status(s: str):
    s = (s or "").lower()
    return ("queue" in s) or ("run" in s) or ("process" in s) or ("start" in s)

@app.delete("/runs/{run_id}", response_model=DeleteRunResponse)
def delete_run(run_id: str, force: bool = Query(default=False)):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")

    job = db.get_job_by_run_id(run_id)
    st = (job.get("status") if job else r.get("status")) or ""
    if _is_active_status(st) and not force:
        raise HTTPException(status_code=409, detail="run is active; use force=true")

    p = _safe_run_dir(run_id)
    if p.exists():
        try:
            shutil.rmtree(p)
        except Exception:
            raise HTTPException(status_code=500, detail="failed to delete run directory")

    db.delete_run(run_id)
    return DeleteRunResponse(ok=True, run_id=run_id)

@app.delete("/runs", response_model=DeleteAllRunsResponse)
def delete_all_runs(confirm: bool = Query(default=False), force: bool = Query(default=False)):
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true required")

    deleted: list[str] = []
    skipped: list[str] = []
    failed: dict[str, str] = {}

    rows = db.list_all_runs()
    for x in rows:
        rid = x["run_id"]
        job = db.get_job_by_run_id(rid)
        st = (job.get("status") if job else x.get("status")) or ""
        if _is_active_status(st) and not force:
            skipped.append(rid)
            continue

        try:
            p = _safe_run_dir(rid)
        except Exception:
            failed[rid] = "invalid run_id"
            continue

        if p.exists():
            try:
                shutil.rmtree(p)
            except Exception:
                failed[rid] = "failed to delete run directory"
                continue

        ok = db.delete_run(rid)
        if ok:
            deleted.append(rid)
        else:
            failed[rid] = "db delete failed"

    return DeleteAllRunsResponse(ok=True, deleted=deleted, skipped=skipped, failed=failed)