from pathlib import Path
import uuid
import orjson
from typing import Any, Dict

def new_id(prefix: str):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def ensure_run_dirs(run_dir: Path):
    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "tracknet").mkdir(parents=True, exist_ok=True)

def write_json(path: Path, obj: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(obj, option=orjson.OPT_INDENT_2))

def read_json(path: Path):
    return orjson.loads(path.read_bytes())