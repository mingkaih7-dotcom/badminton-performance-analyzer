"""Replay archived predictions on a synthetic background; no model or match video."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ANALYZER_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ANALYZER_ROOT.parent
sys.path.insert(0, str(ANALYZER_ROOT / "src"))

from badminton_analyzer.io import read_shuttle_csv
from badminton_analyzer.pipeline import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ANALYZER_ROOT / "outputs" / "run_sample")
    args = parser.parse_args()
    sample = REPOSITORY_ROOT / "examples" / "sample_run"
    df = read_shuttle_csv(sample / "shuttle.csv")
    num_frames = int(df["Frame"].max()) + 1
    out = args.out.resolve()
    video = out / "input" / "synthetic_background.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (1920, 1080))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create the synthetic background video")
    try:
        for frame_number in range(num_frames):
            image = np.full((1080, 1920, 3), 24, dtype=np.uint8)
            cv2.putText(image, "ARCHIVED TRAJECTORY REPLAY - SYNTHETIC BACKGROUND",
                        (40, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
            cv2.putText(image, f"Frame {frame_number} | No model inference | Predictions, not ground truth",
                        (40, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
            writer.write(image)
    finally:
        writer.release()

    run(video, sample / "shuttle.csv", out, ANALYZER_ROOT / "configs" / "default.yaml")
    actual_metrics = json.loads((out / "metrics" / "metrics.json").read_text(encoding="utf-8"))
    expected_metrics = json.loads((sample / "metrics.json").read_text(encoding="utf-8"))
    actual_events = json.loads((out / "events" / "events.json").read_text(encoding="utf-8"))
    expected_events = json.loads((sample / "events.json").read_text(encoding="utf-8"))
    if actual_metrics != expected_metrics or actual_events != expected_events:
        raise RuntimeError("Replay differs from the archived submission outputs")
    print("Replay passed: metrics and events match the archived submission.")
    print("This verifies post-processing, not tracking accuracy.")
    print(f"Results: {out}")


if __name__ == "__main__":
    main()
