# Analysis pipeline

This folder contains trajectory processing, rally and hit estimation, metrics, visualisation and the Streamlit dashboard.

See the [repository README](../README.md) for the CPU demo and [setup instructions](../docs/SETUP.md) for the complete application.

```powershell
python scripts/run_pipeline.py --video path/to/match.mp4 --shuttle_csv path/to/shuttle.csv --out outputs/run_custom
```

All three arguments are required. The CSV must contain `Frame`, `Visibility`, `X`, `Y`. This entry point consumes precomputed tracking data; full model inference is orchestrated by the backend.
