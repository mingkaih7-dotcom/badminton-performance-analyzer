import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from badminton_analyzer.pipeline import run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--shuttle_csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "default.yaml"))
    ap.add_argument("--court_calib", default=None)
    args = ap.parse_args()

    out = run(args.video, args.shuttle_csv, args.out, args.config, court_calib_path=args.court_calib)
    print(out)

if __name__ == "__main__":
    main()