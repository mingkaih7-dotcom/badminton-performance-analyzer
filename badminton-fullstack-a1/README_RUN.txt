Badminton Performance Analyzer (Local)

Full setup and model instructions: ../docs/SETUP.md
CPU demo and overview: ../README.md

After installing backend, analyzer, TrackNetV3 and frontend dependencies
and downloading the official checkpoints:

Run: double-click start.bat
Stop: double-click stop.bat

The launcher creates output/log directories on first use, checks required
checkpoints and starts background services. It opens:
http://127.0.0.1:4200/upload

Logs: badminton-fullstack-a1/logs/
Outputs: badminton-performance-analyzer/outputs/run_*/
Database: badminton-fullstack-a1/data/meta.db (created automatically)

If startup fails, read the prerequisite message and logs. If a port is occupied,
stop the earlier instance before restarting. Model inference has additional
hardware and dependency requirements; the CPU demo does not require weights.
