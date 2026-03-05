Badminton Performance Analyzer (Local)

Folder layout (recommended):
computing project/
  badminton-fullstack-a1/
  badminton-performance-analyzer/
  TrackNetV3/

Prerequisites:
- Node.js (LTS) installed, "npm" available
- Python installed (you must have the .venv folders created already for each project)

First time setup (only once):
1) backend:
   cd badminton-fullstack-a1\backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2) frontend:
   cd badminton-fullstack-a1\frontend
   npm install

3) analyzer:
   cd badminton-performance-analyzer
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

4) tracknet:
   cd TrackNetV3
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   (ensure model weights exist as required)

Run:
- Double click: badminton-fullstack-a1\start.bat
- It opens the web app automatically:
  http://127.0.0.1:4200/upload

Stop:
- Double click: badminton-fullstack-a1\stop.bat

Troubleshooting:
- If a port is already in use:
  run stop.bat or close existing terminal windows (Backend/Frontend/Streamlit).
- If Advanced always shows the same run:
  ensure Streamlit is running app_multi.py and the URL includes ?run_id=run_xxx