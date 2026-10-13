# Contribution and third-party code

This repository combines a final-year project implementation with third-party tracking source.

## Project implementation

The submitted report describes the author's work on:

- FastAPI endpoints and the connection between uploaded videos, processing jobs and stored runs.
- Angular upload, status, run-list and results pages.
- Python trajectory processing, visibility-based rally segmentation, heuristic hit-event estimation and summary metrics.
- Trajectory overlays, visualisation tools and Streamlit integration.
- CSV/JSON artefacts, FFmpeg conversion and consistency of results across the frontend and backend.

The report acknowledged AI-assisted refinement in several files. This repository does not claim that all files or algorithms were written without assistance.

## TrackNetV3

`TrackNetV3/` includes upstream model, training, inference and evaluation code from [qaz812345/TrackNetV3](https://github.com/qaz812345/TrackNetV3). The original MIT licence and README are preserved.

The upstream model and corrected test labels are not original project contributions. Integrating pretrained inference does not constitute training a new model. `make_overlay.py` is a helper distributed in this project snapshot; its presence is not a claim that the underlying tracking model was authored here.

`requirements-inference.txt` is a setup addition for this repository; it does not replace the upstream research dependency file.

## Public repository preparation

README/setup/evaluation documentation, the CPU replay demo, startup fixes and regression checks were added after the academic submission with AI assistance. The original submission files were not modified. These additions are maintenance work, not retrospective claims about the submitted evaluation.

## Licensing

TrackNetV3 remains covered by its existing MIT licence. No new licence for the author's remaining coursework is selected during this cleanup. Public visibility alone does not grant unrestricted reuse of all repository content.
