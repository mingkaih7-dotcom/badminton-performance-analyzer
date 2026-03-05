from pathlib import Path
import pandas as pd
import cv2
import json

def read_video_meta(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    return {"path": str(video_path), "fps": float(fps), "num_frames": nframes, "width": w, "height": h}

def read_shuttle_csv(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    required = {"Frame", "Visibility", "X", "Y"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"CSV missing columns. Need {sorted(required)}, got {list(df.columns)}")
    df = df.sort_values("Frame").reset_index(drop=True)
    df["Frame"] = df["Frame"].astype(int)
    df["Visibility"] = df["Visibility"].astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    return df

def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)

def write_json(path, obj):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path, df):
    path = Path(path)
    ensure_dir(path.parent)
    df.to_csv(path, index=False)
