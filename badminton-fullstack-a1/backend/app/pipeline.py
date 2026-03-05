import os
from pathlib import Path
import shutil
import subprocess
import time
import csv
import orjson

def _which(name: str):
    try:
        return shutil.which(name)
    except Exception:
        return None

def _run(cmd, cwd: Path | None = None):
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def _log_append(log_path: Path, s: str):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(s.rstrip() + "\n")

def transcode_h264(src: Path, dst: Path):
    ffmpeg = _which("ffmpeg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not ffmpeg:
        shutil.copyfile(src, dst)
        return True, "ffmpeg_not_found_copy"
    cmd = [ffmpeg, "-y", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    code, out = _run(cmd)
    if code != 0:
        shutil.copyfile(src, dst)
        return False, out
    return True, out

def find_ball_csv(out_dir: Path):
    if not out_dir.exists():
        return None
    cands = list(out_dir.glob("*_ball.csv"))
    if cands:
        return cands[0]
    p = out_dir / "input_ball.csv"
    if p.exists():
        return p
    any_csv = list(out_dir.glob("*.csv"))
    return any_csv[0] if any_csv else None

def normalize_ball_csv(src: Path, dst: Path):
    rows = []
    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise RuntimeError("empty csv")
        header = [h.strip() for h in header]
        lower = {h.lower(): h for h in header}

        def pick(cands):
            for c in cands:
                if c in lower:
                    return lower[c]
            return None

        c_frame = pick(["frame", "frames"])
        c_x = pick(["x"])
        c_y = pick(["y"])
        c_v = pick(["visibility", "vis", "visible", "v"])
        if not all([c_frame, c_x, c_y, c_v]):
            raise RuntimeError("csv columns not compatible")

        idx = {h: header.index(h) for h in header}

        for r in reader:
            if not r:
                continue
            try:
                fr = int(float(r[idx[c_frame]]))
            except Exception:
                continue
            try:
                x = float(r[idx[c_x]])
            except Exception:
                x = float("nan")
            try:
                y = float(r[idx[c_y]])
            except Exception:
                y = float("nan")
            try:
                v = int(float(r[idx[c_v]]))
            except Exception:
                v = 0
            rows.append((fr, x, y, v))

    rows.sort(key=lambda t: t[0])
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Frame", "X", "Y", "Visibility"])
        for fr, x, y, v in rows:
            w.writerow([fr, x, y, v])

def run_tracknet(tracknet_root: Path, py_exec: str, video_path: Path, save_dir: Path, params: dict):
    predict_py = tracknet_root / "predict.py"
    if not predict_py.exists():
        raise RuntimeError("TrackNetV3 predict.py not found")

    tracknet_ckpt = params.get("tracknet_ckpt") or os.getenv("TRACKNET_CKPT", "ckpts/TrackNet_best.pt")
    inpaint_ckpt = params.get("inpaint_ckpt") or os.getenv("INPAINT_CKPT", "ckpts/InpaintNet_best.pt")

    max_sample_num = int(params.get("max_sample_num", 600))
    batch_size = int(params.get("batch_size", 8))
    num_workers = int(params.get("num_workers", 0))
    large_video = bool(params.get("large_video", True))
    video_range = params.get("video_range", None)

    save_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        py_exec,
        str(predict_py),
        "--video_file", str(video_path),
        "--tracknet_file", str(tracknet_root / tracknet_ckpt),
        "--inpaintnet_file", str(tracknet_root / inpaint_ckpt),
        "--save_dir", str(save_dir),
        "--num_workers", str(num_workers),
        "--batch_size", str(batch_size),
        "--max_sample_num", str(max_sample_num),
    ]
    if large_video:
        cmd.append("--large_video")
    if isinstance(video_range, str) and "," in video_range:
        cmd += ["--video_range", video_range]

    code, out = _run(cmd, cwd=tracknet_root)
    if code != 0:
        raise RuntimeError("TrackNetV3 predict failed")
    return out

def run_analyzer_pipeline(analyzer_root: Path, py_exec: str, video_path: Path, shuttle_csv: Path, out_dir: Path, params: dict):
    script = analyzer_root / "scripts" / "run_pipeline.py"
    if not script.exists():
        raise RuntimeError("analyzer scripts/run_pipeline.py not found")

    config_path = params.get("config_path", None)
    court_calib = params.get("court_calib", None)

    cmd = [py_exec, str(script), "--video", str(video_path), "--shuttle_csv", str(shuttle_csv), "--out", str(out_dir)]
    if isinstance(config_path, str) and config_path:
        cmd += ["--config", config_path]
    if isinstance(court_calib, str) and court_calib:
        cmd += ["--court_calib", court_calib]

    code, out = _run(cmd, cwd=analyzer_root)
    if code != 0:
        raise RuntimeError("analyzer pipeline failed")
    return out

def _first_existing(paths):
    for p in paths:
        if p and p.exists():
            return p
    return None

def _first_glob(dir_path: Path, patterns):
    if not dir_path.exists():
        return None
    for pat in patterns:
        xs = sorted(dir_path.glob(pat))
        if xs:
            return xs[0]
    return None

def _load_json_if_exists(p: Path):
    if not p.exists():
        return {}
    try:
        return orjson.loads(p.read_bytes())
    except Exception:
        return {}

def _events_json_to_rows(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("events"), list):
            obj = obj.get("events")
        elif isinstance(obj.get("data"), list):
            obj = obj.get("data")
        else:
            return []
    if not isinstance(obj, list):
        return []
    rows = []
    for x in obj:
        if isinstance(x, dict):
            rows.append(x)
    return rows

def ensure_events_csv(events_json: Path, out_csv: Path):
    if not events_json.exists():
        return None
    if out_csv.exists():
        return out_csv
    obj = _load_json_if_exists(events_json)
    rows = _events_json_to_rows(obj)
    if not rows:
        return None
    keys = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out_csv

def build_manifest(run_dir: Path, params: dict):
    input_original = _first_existing([run_dir / "input" / "original.mp4", run_dir / "input" / "upload.mp4"])
    input_h264 = _first_existing([run_dir / "input" / "input_h264.mp4"])

    tracknet_ball = _first_existing([
        run_dir / "tracknet" / "ball.csv",
        _first_glob(run_dir / "tracknet", ["*_ball.csv", "input_ball.csv", "*.csv"]) if (run_dir / "tracknet").exists() else None
    ])

    shuttle_csv = _first_existing([
        run_dir / "tracks" / "shuttle.csv",
        _first_glob(run_dir / "tracks", ["*shuttle*.csv", "*.csv"]) if (run_dir / "tracks").exists() else None
    ])

    events_json = _first_existing([
        run_dir / "events" / "events.json",
        _first_glob(run_dir / "events", ["*events*.json", "*.json"]) if (run_dir / "events").exists() else None
    ])

    events_csv = _first_existing([
        run_dir / "events" / "events.csv",
        _first_glob(run_dir / "events", ["*events*.csv", "*.csv"]) if (run_dir / "events").exists() else None
    ])

    if events_json and not events_csv:
        maybe = ensure_events_csv(events_json, run_dir / "events" / "events.csv")
        if maybe and maybe.exists():
            events_csv = maybe

    metrics_json = _first_existing([
        run_dir / "metrics" / "metrics.json",
        run_dir / "metrics.json"
    ])

    rallies_csv = _first_existing([
        run_dir / "rallies" / "rallies.csv",
        _first_glob(run_dir / "rallies", ["*rallies*.csv", "*.csv"]) if (run_dir / "rallies").exists() else None
    ])

    overlay_h264 = _first_existing([
        run_dir / "viz" / "overlay_h264.mp4",
        run_dir / "overlay_h264.mp4"
    ])
    overlay_raw = _first_existing([
        run_dir / "viz" / "overlay_raw.mp4",
        run_dir / "overlay.mp4"
    ])
    overlay = overlay_h264 if overlay_h264 else overlay_raw

    heatmap = _first_existing([
        run_dir / "viz" / "heatmap.png",
        _first_glob(run_dir / "viz", ["*heatmap*.png"]) if (run_dir / "viz").exists() else None
    ])

    video_json = _first_existing([run_dir / "video.json"])
    params_json = _first_existing([run_dir / "params.json"])
    logs = _first_existing([run_dir / "logs.txt"])

    def rel(p: Path):
        return str(p.relative_to(run_dir))

    artifacts = {}
    if input_original: artifacts["input_original"] = rel(input_original)
    if input_h264: artifacts["input_h264"] = rel(input_h264)
    if tracknet_ball: artifacts["tracknet_ball_csv"] = rel(tracknet_ball)
    if shuttle_csv: artifacts["shuttle_csv"] = rel(shuttle_csv)
    if events_json: artifacts["events_json"] = rel(events_json)
    if events_csv: artifacts["events_csv"] = rel(events_csv)
    if metrics_json: artifacts["metrics_json"] = rel(metrics_json)
    if rallies_csv: artifacts["rallies_csv"] = rel(rallies_csv)
    if overlay: artifacts["overlay"] = rel(overlay)
    if heatmap: artifacts["heatmap"] = rel(heatmap)
    if video_json: artifacts["video_json"] = rel(video_json)
    if params_json: artifacts["params_json"] = rel(params_json)
    if logs: artifacts["logs_txt"] = rel(logs)

    metrics = _load_json_if_exists(metrics_json) if metrics_json else {}

    mpath = run_dir / "manifest.json"
    mpath.write_bytes(orjson.dumps({"run_id": run_dir.name, "params": params, "artifacts": artifacts, "metrics": metrics}, option=orjson.OPT_INDENT_2))
    return artifacts, metrics

def run_full_pipeline(run_dir: Path, upload_video: Path, tracknet_root: Path, tracknet_py: str, analyzer_root: Path, analyzer_py: str, params: dict):
    log_path = run_dir / "logs.txt"
    def log(s: str):
        _log_append(log_path, s)

    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "tracknet").mkdir(parents=True, exist_ok=True)

    original = run_dir / "input" / "original.mp4"
    shutil.copyfile(upload_video, original)
    log(str(original))

    input_h264 = run_dir / "input" / "input_h264.mp4"
    ok, out = transcode_h264(original, input_h264)
    log(str(ok))
    if out:
        log(out)

    save_dir = run_dir / "tracknet"
    t0 = time.time()
    out1 = run_tracknet(tracknet_root, tracknet_py, input_h264, save_dir, params)
    log(out1)
    log(str(time.time() - t0))

    ball_csv = find_ball_csv(save_dir)
    if not ball_csv:
        raise RuntimeError("ball csv not found")
    norm_csv = run_dir / "tracknet" / "ball.csv"
    normalize_ball_csv(ball_csv, norm_csv)
    log(str(norm_csv))

    t1 = time.time()
    out2 = run_analyzer_pipeline(analyzer_root, analyzer_py, input_h264, norm_csv, run_dir, params)
    log(out2)
    log(str(time.time() - t1))

    raw_overlay = run_dir / "viz" / "overlay_raw.mp4"
    h264_overlay = run_dir / "viz" / "overlay_h264.mp4"
    if raw_overlay.exists():
        ok2, out3 = transcode_h264(raw_overlay, h264_overlay)
        log(str(ok2))
        if out3:
            log(out3)

    artifacts, metrics = build_manifest(run_dir, params)
    log("done")
    return artifacts, metrics