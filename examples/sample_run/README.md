# Archived submission outputs

These files are copied from the submitted project's `run_4a0de3626156`:

- `shuttle.csv`: frame-level predicted coordinates and visibility, not manual labels.
- `events.csv` and `events.json`: heuristic estimated hit events.
- `metrics.json`: estimated rally and hit summaries.
- `trajectory.png`: original generated image-space visualisation, without match footage.

The source video metadata was 30 FPS, 316 frames, 1920 x 1080. Local paths and the original broadcast videos are not included.

Run `badminton-performance-analyzer/scripts/demo.py` from the repository root to replay these coordinates on a synthetic background. The demo compares regenerated outputs with the archived files; it does not validate the model against ground truth.
