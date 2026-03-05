import os
from pathlib import Path
import orjson
from app.db import DB
from app.paths import runs_root, db_path, tracknet_root, analyzer_root
from app.pipeline import run_full_pipeline

db = DB(db_path())

def run_job(job_id: str, run_id: str, upload_path: str, params: dict):
    run_dir = runs_root() / run_id
    db.update_job(job_id, status="running", progress=3)
    db.set_run(run_id, status="running", params_json=orjson.dumps(params).decode("utf-8"))

    tr = tracknet_root()
    ar = analyzer_root()
    if not tr.exists():
        db.update_job(job_id, status="failed", progress=100, error="TRACKNET_ROOT not found")
        db.set_run(run_id, status="failed")
        return
    if not ar.exists():
        db.update_job(job_id, status="failed", progress=100, error="ANALYZER_ROOT not found")
        db.set_run(run_id, status="failed")
        return

    tracknet_py = os.getenv("TRACKNET_PY", "python")
    analyzer_py = os.getenv("ANALYZER_PY", "python")

    try:
        db.update_job(job_id, progress=10)
        artifacts, metrics = run_full_pipeline(run_dir, Path(upload_path), tr, tracknet_py, ar, analyzer_py, params)
        db.update_job(job_id, progress=95)
        db.set_run(
            run_id,
            status="finished",
            artifacts_json=orjson.dumps(artifacts).decode("utf-8"),
            metrics_json=orjson.dumps(metrics).decode("utf-8"),
        )
        db.update_job(job_id, status="finished", progress=100)
    except Exception as e:
        msg = str(e)
        db.update_job(job_id, status="failed", progress=100, error=msg)
        db.set_run(run_id, status="failed")
        p = run_dir / "logs.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
        raise