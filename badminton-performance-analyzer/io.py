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
    return {"path": str(video_path), "fps": float(fps), "frames": nframes, "num_frames": nframes, "width": w, "height": h}

def _pick_col(lower_to_orig, candidates):
    for c in candidates:
        if c in lower_to_orig:
            return lower_to_orig[c]
    return None

def read_shuttle_csv(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    lower_to_orig = {c.lower(): c for c in df.columns}

    c_frame = _pick_col(lower_to_orig, ["frame", "frames", "frm"])
    c_x = _pick_col(lower_to_orig, ["x", "pos_x", "x_coord", "xcoordinate"])
    c_y = _pick_col(lower_to_orig, ["y", "pos_y", "y_coord", "ycoordinate"])
    c_vis = _pick_col(lower_to_orig, ["visibility", "vis", "visible", "v"])

    if not all([c_frame, c_x, c_y, c_vis]):
        raise ValueError(f"CSV missing columns. Need Frame/X/Y/Visibility (case-insensitive). Got {list(df.columns)}")

    df = df[[c_frame, c_x, c_y, c_vis]].copy()
    df.columns = ["Frame", "X", "Y", "Visibility"]

    df["Frame"] = pd.to_numeric(df["Frame"], errors="coerce").fillna(-1).astype(int)
    df = df[df["Frame"] >= 0]
    df["Visibility"] = pd.to_numeric(df["Visibility"], errors="coerce").fillna(0).astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    df = df.sort_values("Frame").reset_index(drop=True)
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