import argparse
from pathlib import Path
import pandas as pd
import cv2
import numpy as np

state = {"x": None, "y": None, "clicked": False}

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        state["x"] = x
        state["y"] = y
        state["clicked"] = True

def main(video_path, shuttle_csv, out_csv):
    df = pd.read_csv(shuttle_csv)
    df.columns = [c.strip() for c in df.columns]
    required = {"Frame", "Visibility", "X", "Y"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"CSV missing columns. Need {sorted(required)}, got {list(df.columns)}")
    df = df.sort_values("Frame").reset_index(drop=True)
    df["Frame"] = df["Frame"].astype(int)
    df["Visibility"] = df["Visibility"].astype(int)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    win = "Correct Shuttle Labels"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, on_mouse)

    idx_map = {int(f): i for i, f in enumerate(df["Frame"].tolist())}
    frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        i = idx_map.get(frame_idx, None)
        if i is not None and int(df.loc[i, "Visibility"]) == 1:
            x = df.loc[i, "X"]
            y = df.loc[i, "Y"]
            if np.isfinite(x) and np.isfinite(y):
                cv2.circle(frame, (int(x), int(y)), 6, (0, 0, 255), -1)

        cv2.putText(frame, f"Frame {frame_idx}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(frame, "a/d prev/next | v toggle vis | click set xy | s save | q quit", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if state["clicked"]:
            if i is not None:
                df.loc[i, "Visibility"] = 1
                df.loc[i, "X"] = float(state["x"])
                df.loc[i, "Y"] = float(state["y"])
            state["clicked"] = False

        cv2.imshow(win, frame)
        k = cv2.waitKey(10) & 0xFF

        if k == ord("q"):
            break
        if k == ord("d"):
            frame_idx += 1
        if k == ord("a"):
            frame_idx = max(0, frame_idx - 1)
        if k == ord("v"):
            if i is not None:
                df.loc[i, "Visibility"] = 0 if int(df.loc[i, "Visibility"]) == 1 else 1
        if k == ord("s"):
            out = Path(out_csv)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out, index=False)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--shuttle_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()
    main(args.video, args.shuttle_csv, args.out_csv)
