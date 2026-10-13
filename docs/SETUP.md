# Setup and running

## CPU analysis demo

The quickest route is the root README's CPU demo. It requires Python 3.10-3.12 and the analyzer requirements only. No CUDA, model checkpoint, Redis, original match video or Node.js is required.

## Complete application on Windows

Use Python 3.10 for the legacy TrackNetV3 environment. Use Node.js 22.12 or newer in the supported Node 22 line for Angular 21, following [Angular's compatibility table](https://angular.dev/reference/versions). Install FFmpeg and make `ffmpeg` available on PATH for browser-compatible H.264 video output.

Run the following from the repository root:

```powershell
python -m venv badminton-fullstack-a1/backend/.venv
badminton-fullstack-a1/backend/.venv/Scripts/python.exe -m pip install --no-compile -r badminton-fullstack-a1/backend/requirements.txt

python -m venv badminton-performance-analyzer/.venv
badminton-performance-analyzer/.venv/Scripts/python.exe -m pip install --no-compile -r badminton-performance-analyzer/requirements.txt

cd badminton-fullstack-a1/frontend
npm ci
cd ../..
```

### TrackNetV3

Create a separate Python 3.10 environment so that legacy model dependencies do not constrain the dashboard:

```powershell
py -3.10 -m venv TrackNetV3/.venv
TrackNetV3/.venv/Scripts/python.exe -m pip install --no-compile -r TrackNetV3/requirements-inference.txt
```

Install a PyTorch build appropriate for your machine using the [official PyTorch installation instructions](https://pytorch.org/get-started/previous-versions/). The vendored source predates the [PyTorch 2.6 checkpoint-loading default change](https://docs.pytorch.org/docs/stable/notes/serialization.html#torch-load-with-weights-only-true); the upstream requirements pin PyTorch 1.10. A Python 3.10-compatible PyTorch 1.13.1 build is a legacy starting point, but full model inference has not been revalidated during this repository cleanup. Match the CUDA wheel to your driver and verify it locally before claiming support for a particular hardware configuration.

`requirements-inference.txt` covers the non-PyTorch imports needed by `predict.py`, including `tqdm` and `pycocotools`, which are missing from the upstream requirements. It uses NumPy 1.23.5 rather than the upstream NumPy 1.22.4 pin to meet pandas 2.0's minimum dependency.

Download the pretrained weights through the [upstream checkpoint link](https://drive.google.com/file/d/1CfzE87a0f6LhBp0kniSl1-89zaLCZ8cA/view?usp=sharing) linked in the [original inference instructions](../TrackNetV3/README.md#inference). Extract:

```text
TrackNetV3/ckpts/TrackNet_best.pt
TrackNetV3/ckpts/InpaintNet_best.pt
```

Weights are intentionally not tracked by Git. Keep the original checkpoint names. The launcher uses those default locations. The backend also accepts `TRACKNET_CKPT` and `INPAINT_CKPT` environment variables, interpreted relative to `TRACKNET_ROOT`.

Check the model environment without processing a video:

```powershell
TrackNetV3/.venv/Scripts/python.exe -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

### Launch

```powershell
badminton-fullstack-a1/start.bat
```

The launcher checks prerequisites and checkpoint locations, creates the output and log folders, and starts background processes. The browser opens the upload page. Logs are saved in `badminton-fullstack-a1/logs/`.

The bundled launcher uses synchronous job execution (`RQ_SYNC=1`); Redis is not needed for that local mode. Async worker configuration is outside this quick start.

Stop the application with `badminton-fullstack-a1/stop.bat`. The launcher records its own process IDs; the stop script stops only those recorded processes.

### Troubleshooting

- **Missing virtual environment or weights:** complete the setup above; never upload your environment to GitHub.
- **Port in use:** stop the previous instance; the launcher refuses to overwrite an existing service on 8000, 4200 or 8501.
- **Processing fails:** inspect the backend log and the selected run's `logs.txt`.
- **Video does not play:** verify FFmpeg is available. The fallback copy does not guarantee H.264 browser compatibility.
- **Streamlit shows no runs:** complete an analysis first or run the CPU demo in the same analyzer folder.
- **Backend launched manually:** its default sibling paths now resolve from the repository location. Override `ANALYZER_ROOT`, `TRACKNET_ROOT`, `RUNS_ROOT` or `DB_PATH` when using a different layout.

## Frontend checks

```powershell
cd badminton-fullstack-a1/frontend
npm ci
npm run build -- --configuration development
```

The development build matches the local prototype workflow. Production bundle size limits are a separate concern; this cleanup does not introduce a hosted deployment.
