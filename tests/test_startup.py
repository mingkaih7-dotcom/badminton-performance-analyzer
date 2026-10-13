import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "badminton-fullstack-a1" / "backend" / "app"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths = load_module("project_paths", BACKEND_APP / "paths.py")
db_module = load_module("project_db", BACKEND_APP / "db.py")


class StartupTests(unittest.TestCase):
    def test_defaults_do_not_depend_on_working_directory(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(paths.analyzer_root(), ROOT / "badminton-performance-analyzer")
            self.assertEqual(paths.tracknet_root(), ROOT / "TrackNetV3")
            self.assertEqual(paths.runs_root(), ROOT / "badminton-performance-analyzer" / "outputs")

    def test_explicit_run_directory_is_used_before_it_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "new" / "runs"
            with patch.dict("os.environ", {"RUNS_ROOT": str(target)}, clear=True):
                self.assertEqual(paths.runs_root(), target)
                self.assertFalse(target.exists())

    def test_fresh_database_creates_parent_and_persists_a_job(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "fresh" / "data" / "meta.db"
            db = db_module.DB(database)
            self.assertEqual(db.list_runs(), [])
            db.create_job("job_test", "run_test")
            reopened = db_module.DB(database)
            self.assertEqual(reopened.get_job("job_test")["status"], "queued")
            self.assertEqual(reopened.get_run("run_test")["status"], "queued")


if __name__ == "__main__":
    unittest.main()
