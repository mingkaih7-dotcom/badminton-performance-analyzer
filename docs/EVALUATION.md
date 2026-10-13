# Evaluation and limitations

## Submitted project evaluation

The final report describes functional checks of video upload, job creation, run retrieval, analytics loading and artefact access, together with frontend/backend integration and visual inspection of outputs. Robustness was partially successful: processing remained functional, while tracking quality worsened with camera changes, motion blur and occlusion.

There was no comprehensive frame-level labelled ground truth or independent accuracy benchmark. The original system was an academic prototype.

## Archived example

The small files under `examples/sample_run/` were taken from the final submitted code package's `run_4a0de3626156` outputs. They retain the generated numbers:

| Property | Output |
| --- | --- |
| Video metadata | 316 frames at 30 FPS, 1920 x 1080 |
| Estimated rallies | 1 |
| Estimated hit events | 32 |
| Estimated rally duration | 10.5333 seconds |

The estimates must not be described as verified real hit counts, detection accuracy or proof of coaching effectiveness. Tracking jumps can inflate downstream event counts.

The Streamlit dashboard independently recalculates events with its interactive thresholds. With its default settings it can display a different count (69 candidates on this example) from the archived pipeline's 32 candidates. These are different heuristic settings, not two ground-truth measurements. The dashboard now labels them as estimates and explains that visibility coverage is not accuracy.

The PNG is an image-plane trajectory visualisation. Its coordinates are not calibrated court positions. Homography of an airborne shuttle is not a physical 3D landing reconstruction.

Original broadcast footage, model weights, logs containing local paths and runtime database records are excluded from these public examples.

## Checks added during public repository preparation

- CPU replay of the archived CSV through the real analysis pipeline, comparing generated metrics and event records with the archived output.
- Regression checks of default/overridden paths and SQLite creation in a fresh nested directory.
- Python syntax checks and PowerShell parser checks.
- Angular development build.
- Streamlit rendering of the CPU replay, including the event table and charts.

These checks passed on 13 October 2026 using Windows, Python 3.12, NumPy 1.26.4, pandas 2.3.3, OpenCV 4.11.0, Streamlit 1.49.1, PyArrow 17.0.0 and Node.js 22.22.2. The three startup/database regression tests passed. The CPU replay reproduced the archived metrics and events exactly; the Streamlit render completed without exceptions. The Angular development build passed. The launcher scripts were parsed, but the full model-backed launch was not executed.

The CPU demo's background is synthetic. It tests post-processing and visualisation, not TrackNetV3 localisation accuracy. Full inference with model checkpoints, CUDA execution and the complete browser upload workflow require separate verification on the user's configured machine.

## Future work

Priority improvements are labelled evaluation clips, temporal handling of camera changes/missing detections, validation of hit/rally estimates, broader test footage and completed player analysis. None of these are presented as delivered features.
