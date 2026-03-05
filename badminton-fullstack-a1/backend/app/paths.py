import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _get_env_path(name: str):
    v = os.getenv(name, "")
    v = v.strip()
    if not v:
        return None
    return Path(v)

def analyzer_root() -> Path:
    p = _get_env_path("ANALYZER_ROOT")
    return p if p else Path()

def tracknet_root() -> Path:
    p = _get_env_path("TRACKNET_ROOT")
    return p if p else Path()

def runs_root() -> Path:
    rr = _get_env_path("RUNS_ROOT")
    if rr and rr.exists():
        return rr
    ar = analyzer_root()
    if ar.exists():
        return ar / "outputs"
    return ROOT / "data" / "runs"

def db_path() -> Path:
    p = _get_env_path("DB_PATH")
    if p:
        return p
    return ROOT / "data" / "meta.db"