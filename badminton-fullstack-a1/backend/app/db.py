import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class DB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _conn(self):
        connection = sqlite3.connect(str(self.db_path))
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _init(self):
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  job_id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  status TEXT NOT NULL,
                  progress INTEGER NOT NULL,
                  error TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                  run_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  params_json TEXT NOT NULL,
                  artifacts_json TEXT NOT NULL,
                  metrics_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )

    def create_job(self, job_id: str, run_id: str):
        now = utc_now()
        with self._conn() as con:
            con.execute(
                "INSERT INTO jobs(job_id, run_id, status, progress, error, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (job_id, run_id, "queued", 0, None, now, now),
            )
            con.execute(
                "INSERT INTO runs(run_id, status, params_json, artifacts_json, metrics_json, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (run_id, "queued", "{}", "{}", "{}", now, now),
            )

    def update_job(self, job_id: str, status: Optional[str] = None, progress: Optional[int] = None, error: Optional[str] = None):
        now = utc_now()
        with self._conn() as con:
            row = con.execute("SELECT status, progress, error FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                return
            cur_status, cur_progress, cur_error = row
            ns = status if status is not None else cur_status
            np = int(progress) if progress is not None else int(cur_progress)
            ne = error if error is not None else cur_error
            con.execute(
                "UPDATE jobs SET status=?, progress=?, error=?, updated_at=? WHERE job_id=?",
                (ns, np, ne, now, job_id),
            )

    def set_run(self, run_id: str, status: Optional[str] = None, params_json: Optional[str] = None, artifacts_json: Optional[str] = None, metrics_json: Optional[str] = None):
        now = utc_now()
        with self._conn() as con:
            row = con.execute("SELECT status, params_json, artifacts_json, metrics_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                return
            cur_status, cur_params, cur_art, cur_met = row
            ns = status if status is not None else cur_status
            np = params_json if params_json is not None else cur_params
            na = artifacts_json if artifacts_json is not None else cur_art
            nm = metrics_json if metrics_json is not None else cur_met
            con.execute(
                "UPDATE runs SET status=?, params_json=?, artifacts_json=?, metrics_json=?, updated_at=? WHERE run_id=?",
                (ns, np, na, nm, now, run_id),
            )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute("SELECT job_id, run_id, status, progress, error, updated_at FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                return None
            return {
                "job_id": row[0],
                "run_id": row[1],
                "status": row[2],
                "progress": int(row[3]),
                "error": row[4],
                "updated_at": row[5],
            }

    def get_job_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute(
                "SELECT job_id, run_id, status, progress, error, updated_at FROM jobs WHERE run_id=? ORDER BY updated_at DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "job_id": row[0],
                "run_id": row[1],
                "status": row[2],
                "progress": int(row[3]),
                "error": row[4],
                "updated_at": row[5],
            }

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute("SELECT run_id, status, params_json, artifacts_json, metrics_json, created_at, updated_at FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                return None
            return {
                "run_id": row[0],
                "status": row[1],
                "params_json": row[2],
                "artifacts_json": row[3],
                "metrics_json": row[4],
                "created_at": row[5],
                "updated_at": row[6],
            }

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        n = int(limit) if limit is not None else 50
        if n <= 0:
            n = 50
        if n > 500:
            n = 500
        with self._conn() as con:
            rows = con.execute(
                "SELECT run_id, status, created_at, updated_at FROM runs ORDER BY updated_at DESC LIMIT ?",
                (n,),
            ).fetchall()
            return [{"run_id": r[0], "status": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]

    def list_all_runs(self) -> List[Dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT run_id, status, created_at, updated_at FROM runs ORDER BY updated_at DESC",
            ).fetchall()
            return [{"run_id": r[0], "status": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]

    def delete_run(self, run_id: str) -> bool:
        with self._conn() as con:
            cur = con.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
            con.execute("DELETE FROM jobs WHERE run_id=?", (run_id,))
            return (cur.rowcount or 0) > 0
