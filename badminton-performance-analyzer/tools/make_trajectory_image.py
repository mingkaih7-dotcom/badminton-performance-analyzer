import argparse
import math
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

def _read_csv(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}
    need = ["frame", "x", "y", "visibility"]
    if not all(k in lower for k in need):
        raise ValueError(f"CSV columns must include Frame/X/Y/Visibility (case-insensitive). Got: {list(df.columns)}")
    df = df[[lower["frame"], lower["x"], lower["y"], lower["visibility"]]].copy()
    df.columns = ["Frame", "X", "Y", "Visibility"]
    df["Frame"] = pd.to_numeric(df["Frame"], errors="coerce").fillna(-1).astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df["Visibility"] = pd.to_numeric(df["Visibility"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("Frame")
    df = df[df["Frame"] >= 0]
    return df

def _get_video_wh(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    if w > 0 and h > 0:
        return (w, h, n)
    return None

def _read_bg_frame(video_path, frame_idx):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    if frame_idx is not None and frame_idx >= 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    return frame

def _hsv_to_bgr(h, s, v):
    h = int(np.clip(h, 0, 179))
    s = int(np.clip(s, 0, 255))
    v = int(np.clip(v, 0, 255))
    hsv = np.uint8([[[h, s, v]]])
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0].tolist()
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))

def _color_time(t):
    h = int(round((1.0 - t) * 160))
    return _hsv_to_bgr(h, 230, 255)

def _color_seg(i):
    h = int((i * 37) % 180)
    return _hsv_to_bgr(h, 230, 255)

def _color_speed(s, s_min, s_max):
    if s_max <= s_min:
        return _hsv_to_bgr(90, 230, 255)
    t = (s - s_min) / (s_max - s_min)
    t = float(np.clip(t, 0.0, 1.0))
    h = int(round((1.0 - t) * 120))
    return _hsv_to_bgr(h, 230, 255)

def _parse_roi(roi_str):
    if not roi_str:
        return None
    parts = [p.strip() for p in roi_str.split(",")]
    if len(parts) != 4:
        raise ValueError("--roi must be x1,y1,x2,y2")
    x1, y1, x2, y2 = [int(float(p)) for p in parts]
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    return (x1, y1, x2, y2)

def _clean_and_segment(fr, xy, max_gap, max_speed, roi):
    segs = []
    cur = []
    prev = None
    prev_f = None

    x1 = y1 = x2 = y2 = None
    if roi is not None:
        x1, y1, x2, y2 = roi

    for f, (x, y) in zip(fr, xy):
        x = float(x)
        y = float(y)

        if roi is not None:
            if not (x1 <= x <= x2 and y1 <= y <= y2):
                if len(cur) >= 2:
                    segs.append(cur)
                cur = []
                prev = None
                prev_f = None
                continue

        if prev is None:
            cur = [(f, x, y)]
            prev = (x, y)
            prev_f = f
            continue

        dt = int(f - prev_f)
        if dt <= 0:
            continue

        if dt > max_gap:
            if len(cur) >= 2:
                segs.append(cur)
            cur = [(f, x, y)]
            prev = (x, y)
            prev_f = f
            continue

        sp = math.hypot(x - prev[0], y - prev[1]) / float(dt)
        if sp > max_speed:
            if len(cur) >= 2:
                segs.append(cur)
            cur = []
            prev = None
            prev_f = None
            continue

        cur.append((f, x, y))
        prev = (x, y)
        prev_f = f

    if len(cur) >= 2:
        segs.append(cur)

    return segs

def _draw_time(overlay, segs, thickness, arrow_step):
    total = sum(len(s) for s in segs)
    if total <= 1:
        return overlay
    idx = 0
    for s in segs:
        pts = [(int(round(x)), int(round(y))) for _, x, y in s]
        for i in range(1, len(pts)):
            t = idx / (total - 1)
            c = _color_time(t)
            cv2.line(overlay, pts[i - 1], pts[i], c, thickness, lineType=cv2.LINE_AA)
            if arrow_step > 0 and (i % arrow_step == 0):
                cv2.arrowedLine(overlay, pts[i - 1], pts[i], c, thickness, tipLength=0.25)
            idx += 1
        idx += 1
    return overlay

def _draw_seg(overlay, segs, thickness, arrow_step):
    for si, s in enumerate(segs):
        c = _color_seg(si)
        pts = [(int(round(x)), int(round(y))) for _, x, y in s]
        for i in range(1, len(pts)):
            cv2.line(overlay, pts[i - 1], pts[i], c, thickness, lineType=cv2.LINE_AA)
            if arrow_step > 0 and (i % arrow_step == 0):
                cv2.arrowedLine(overlay, pts[i - 1], pts[i], c, thickness, tipLength=0.25)
    return overlay

def _draw_speed(overlay, segs, thickness, arrow_step):
    edges = []
    speeds = []
    for s in segs:
        for i in range(1, len(s)):
            f0, x0, y0 = s[i - 1]
            f1, x1, y1 = s[i]
            dt = max(1, int(f1 - f0))
            sp = math.hypot(float(x1 - x0), float(y1 - y0)) / float(dt)
            speeds.append(sp)
            edges.append(((int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))), sp))

    if len(speeds) == 0:
        return overlay

    s_arr = np.array(speeds, dtype=np.float32)
    s_min = float(np.percentile(s_arr, 5))
    s_max = float(np.percentile(s_arr, 95))

    for i, (p0, p1, sp) in enumerate(edges):
        c = _color_speed(sp, s_min, s_max)
        cv2.line(overlay, p0, p1, c, thickness, lineType=cv2.LINE_AA)
        if arrow_step > 0 and (i % arrow_step == 0):
            cv2.arrowedLine(overlay, p0, p1, c, thickness, tipLength=0.25)

    return overlay

def _dim_background(img, dim):
    if dim <= 0:
        return img
    dim = float(np.clip(dim, 0.0, 0.9))
    return cv2.convertScaleAbs(img, alpha=(1.0 - dim), beta=0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["time", "speed", "segment"], default="time")
    ap.add_argument("--roi", default=None)
    ap.add_argument("--max_gap_frames", type=int, default=2)
    ap.add_argument("--max_speed_px_per_frame", type=float, default=120.0)
    ap.add_argument("--downsample", type=int, default=2)
    ap.add_argument("--thickness", type=int, default=2)
    ap.add_argument("--arrow_step", type=int, default=40)
    ap.add_argument("--bg", choices=["frame", "blank"], default="frame")
    ap.add_argument("--bg_frame", type=int, default=-1)
    ap.add_argument("--alpha", type=float, default=0.9)
    ap.add_argument("--dim", type=float, default=0.35)
    ap.add_argument("--min_seg_len", type=int, default=10)
    ap.add_argument("--max_segs", type=int, default=12)
    args = ap.parse_args()

    video_path = Path(args.video)
    csv_path = Path(args.csv)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = _read_csv(csv_path)
    df = df[df["Visibility"] == 1]
    df = df[np.isfinite(df["X"]) & np.isfinite(df["Y"])]
    if len(df) < 2:
        raise RuntimeError("Not enough visible points to draw trajectory")

    if args.downsample < 1:
        args.downsample = 1
    df = df.iloc[::args.downsample].copy()

    whn = _get_video_wh(video_path)
    if whn is None:
        raise RuntimeError(f"Cannot open video: {video_path}")
    w, h, n = whn

    if args.bg == "frame":
        idx = args.bg_frame
        if idx < 0:
            idx = n // 2 if n > 0 else 0
        bg = _read_bg_frame(video_path, idx)
        if bg is None:
            bg = np.zeros((h, w, 3), dtype=np.uint8)
        bg = _dim_background(bg, args.dim)
    else:
        bg = np.zeros((h, w, 3), dtype=np.uint8)

    roi = _parse_roi(args.roi)

    fr = df["Frame"].to_numpy(dtype=np.int32)
    xy = df[["X", "Y"]].to_numpy(dtype=np.float32)

    segs = _clean_and_segment(
        fr,
        xy,
        max_gap=int(args.max_gap_frames),
        max_speed=float(args.max_speed_px_per_frame),
        roi=roi
    )

    segs = [s for s in segs if len(s) >= int(args.min_seg_len)]
    segs.sort(key=lambda s: len(s), reverse=True)
    segs = segs[: int(args.max_segs)]
    segs.sort(key=lambda s: s[0][0])

    if len(segs) == 0:
        raise RuntimeError("All segments removed by cleaning. Try: increase roi, increase max_speed, or lower min_seg_len.")

    overlay = np.zeros_like(bg)

    if args.mode == "time":
        overlay = _draw_time(overlay, segs, int(args.thickness), int(args.arrow_step))
    elif args.mode == "speed":
        overlay = _draw_speed(overlay, segs, int(args.thickness), int(args.arrow_step))
    else:
        overlay = _draw_seg(overlay, segs, int(args.thickness), int(args.arrow_step))

    a = float(np.clip(args.alpha, 0.0, 1.0))
    out = cv2.addWeighted(bg, 1.0, overlay, a, 0.0)

    if roi is not None:
        x1, y1, x2, y2 = roi
        out = out[y1:y2, x1:x2]

    cv2.imwrite(str(out_path), out)

if __name__ == "__main__":
    main()