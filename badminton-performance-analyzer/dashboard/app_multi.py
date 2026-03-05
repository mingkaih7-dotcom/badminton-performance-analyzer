import argparse
from pathlib import Path
import streamlit as st

try:
    from dashboard.app import render
except Exception:
    from app import render

def list_runs(runs_root: Path):
    xs = [p for p in runs_root.glob("run_*") if p.is_dir()]
    xs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return xs

def get_run_id():
    try:
        v = st.query_params.get("run_id", None)
        if isinstance(v, list):
            return v[0] if v else None
        return v
    except Exception:
        qp = st.experimental_get_query_params()
        v = qp.get("run_id", [])
        return v[0] if v else None

def set_run_id(v: str):
    try:
        st.query_params.clear()
        st.query_params["run_id"] = v
    except Exception:
        st.experimental_set_query_params(run_id=v)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs_root", required=True)
    args = ap.parse_args()

    st.set_page_config(page_title="Badminton Performance Analyzer (Advanced)", layout="wide")
    st.title("Badminton Performance Analyzer (Advanced)")

    runs_root = Path(args.runs_root)
    runs = list_runs(runs_root)
    if not runs:
        st.error(f"No run_* folders found under: {runs_root}")
        st.stop()

    names = [p.name for p in runs]
    default_run = get_run_id()
    idx = names.index(default_run) if default_run in names else 0

    with st.sidebar:
        sel = st.selectbox("Select run", names, index=idx)
        if sel != default_run:
            set_run_id(sel)
            st.rerun()

    run_dir = runs_root / sel
    render(str(run_dir))

if __name__ == "__main__":
    main()