import argparse
import json
from pathlib import Path
from io import BytesIO
import math

import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None

def pick_first(paths):
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None

@st.cache_data(show_spinner=False)
def load_shuttle_df(run_dir_str):
    run_dir = Path(run_dir_str)
    p = pick_first([
        run_dir / "tracks" / "shuttle.csv",
        run_dir / "shuttle.csv",
        run_dir / "tracks" / "input_ball.csv",
        run_dir / "input_ball.csv",
    ])
    if not p:
        return None, None
    df = pd.read_csv(p)
    df.columns = [c.strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}
    need = ["frame", "x", "y", "visibility"]
    if not all(k in lower for k in need):
        return None, str(p)
    df = df[[lower["frame"], lower["x"], lower["y"], lower["visibility"]]].copy()
    df.columns = ["Frame", "X", "Y", "Visibility"]
    df["Frame"] = pd.to_numeric(df["Frame"], errors="coerce").fillna(-1).astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df["Visibility"] = pd.to_numeric(df["Visibility"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("Frame")
    df = df[df["Frame"] >= 0]
    return df, str(p)

def open_video_meta(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    if w <= 0 or h <= 0:
        return None
    if fps <= 0:
        fps = 30.0
    return {"width": w, "height": h, "fps": fps, "frames": n}

@st.cache_data(show_spinner=False)
def read_mid_frame(video_path_str):
    p = Path(video_path_str)
    if not p.exists():
        return None
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        return None
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    idx = n // 2 if n > 0 else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    return frame

def hsv_to_bgr(h, s, v):
    h = int(np.clip(h, 0, 179))
    s = int(np.clip(s, 0, 255))
    v = int(np.clip(v, 0, 255))
    hsv = np.uint8([[[h, s, v]]])
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0].tolist()
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))

def color_time(t):
    h = int(round((1.0 - t) * 160))
    return hsv_to_bgr(h, 230, 255)

def color_seg(i):
    h = int((i * 37) % 180)
    return hsv_to_bgr(h, 230, 255)

def color_speed(s, s_min, s_max):
    if s_max <= s_min:
        return hsv_to_bgr(90, 230, 255)
    t = (s - s_min) / (s_max - s_min)
    t = float(np.clip(t, 0.0, 1.0))
    h = int(round((1.0 - t) * 120))
    return hsv_to_bgr(h, 230, 255)

def parse_roi(roi_str):
    if not roi_str:
        return None
    parts = [p.strip() for p in roi_str.split(",")]
    if len(parts) != 4:
        return None
    x1, y1, x2, y2 = [int(float(p)) for p in parts]
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    return (x1, y1, x2, y2)

def clean_and_segment(fr, xy, max_gap, max_speed, roi):
    segs = []
    cur = []
    prev = None
    prev_f = None
    outliers = 0

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
                outliers += 1
                continue

        if prev is None:
            cur = [(f, x, y)]
            prev = (x, y)
            prev_f = f
            continue

        dt = int(f - prev_f)
        if dt <= 0:
            outliers += 1
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
            outliers += 1
            continue

        cur.append((f, x, y))
        prev = (x, y)
        prev_f = f

    if len(cur) >= 2:
        segs.append(cur)

    return segs, outliers

def segment_rallies_from_visible_frames(visible_frames, gap_frames):
    visible_frames = np.array(visible_frames, dtype=np.int32)
    if visible_frames.size == 0:
        return []
    visible_frames.sort()
    rallies = []
    s = int(visible_frames[0])
    prev = int(visible_frames[0])
    for f in visible_frames[1:]:
        f = int(f)
        if (f - prev) > int(gap_frames):
            rallies.append({"start_frame": int(s), "end_frame": int(prev)})
            s = f
        prev = f
    rallies.append({"start_frame": int(s), "end_frame": int(prev)})
    return rallies

def compute_gaps_seconds(visible_frames, fps):
    visible_frames = np.array(visible_frames, dtype=np.int32)
    if visible_frames.size < 2:
        return 0.0, 0
    visible_frames.sort()
    gaps = []
    for a, b in zip(visible_frames[:-1], visible_frames[1:]):
        g = int(b) - int(a) - 1
        if g > 0:
            gaps.append(g / float(fps))
    if len(gaps) == 0:
        return 0.0, 0
    return float(np.mean(gaps)), int(len(gaps))

def detect_hits(df_vis, rallies, fps, hit_speed_th, accel_th, max_gap_frames):
    if len(rallies) == 0 or len(df_vis) < 3:
        return []
    df_vis = df_vis.sort_values("Frame").copy()
    fr = df_vis["Frame"].to_numpy(dtype=np.int32)
    xs = df_vis["X"].to_numpy(dtype=np.float32)
    ys = df_vis["Y"].to_numpy(dtype=np.float32)

    events = []
    for ridx, r in enumerate(rallies):
        s = int(r["start_frame"])
        e = int(r["end_frame"])
        m = (fr >= s) & (fr <= e)
        if not m.any():
            continue
        rf = fr[m]
        rx = xs[m]
        ry = ys[m]
        if rf.size < 3:
            continue

        speeds = np.zeros((rf.size,), dtype=np.float32)
        for i in range(1, rf.size):
            dt = int(rf[i] - rf[i - 1])
            if dt <= 0 or dt > int(max_gap_frames):
                speeds[i] = 0.0
                continue
            d = math.hypot(float(rx[i] - rx[i - 1]), float(ry[i] - ry[i - 1]))
            speeds[i] = float(d / float(dt))

        for i in range(2, rf.size - 1):
            if speeds[i] <= float(hit_speed_th):
                continue
            if not (speeds[i] > speeds[i - 1] and speeds[i] >= speeds[i + 1]):
                continue
            accel = float(speeds[i] - speeds[i - 1])
            if accel < float(accel_th):
                continue
            events.append({
                "type": "hit",
                "frame": int(rf[i]),
                "rally_index": int(ridx),
                "x": int(round(float(rx[i]))),
                "y": int(round(float(ry[i]))),
                "speed": float(speeds[i]),
                "time_sec": float(rf[i] / float(fps))
            })

    return events

def render_trajectory_overlay(canvas_bgr, segs, mode, thickness, arrow_step):
    overlay = np.zeros_like(canvas_bgr)
    if mode == "time":
        total = sum(len(s) for s in segs)
        total = max(total, 1)
        idx = 0
        for s in segs:
            pts = [(int(round(x)), int(round(y))) for _, x, y in s]
            for i in range(1, len(pts)):
                t = idx / (total - 1) if total > 1 else 0.0
                c = color_time(t)
                cv2.line(overlay, pts[i - 1], pts[i], c, int(thickness), lineType=cv2.LINE_AA)
                if int(arrow_step) > 0 and (i % int(arrow_step) == 0):
                    cv2.arrowedLine(overlay, pts[i - 1], pts[i], c, int(thickness), tipLength=0.25)
                idx += 1
            idx += 1
    elif mode == "speed":
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
        if len(speeds) > 0:
            s_arr = np.array(speeds, dtype=np.float32)
            s_min = float(np.percentile(s_arr, 5))
            s_max = float(np.percentile(s_arr, 95))
            for i, (p0, p1, sp) in enumerate(edges):
                c = color_speed(sp, s_min, s_max)
                cv2.line(overlay, p0, p1, c, int(thickness), lineType=cv2.LINE_AA)
                if int(arrow_step) > 0 and (i % int(arrow_step) == 0):
                    cv2.arrowedLine(overlay, p0, p1, c, int(thickness), tipLength=0.25)
    else:
        for si, s in enumerate(segs):
            c = color_seg(si)
            pts = [(int(round(x)), int(round(y))) for _, x, y in s]
            for i in range(1, len(pts)):
                cv2.line(overlay, pts[i - 1], pts[i], c, int(thickness), lineType=cv2.LINE_AA)
                if int(arrow_step) > 0 and (i % int(arrow_step) == 0):
                    cv2.arrowedLine(overlay, pts[i - 1], pts[i], c, int(thickness), tipLength=0.25)
    return overlay

def dim_background(img_bgr, dim):
    dim = float(np.clip(dim, 0.0, 0.9))
    return cv2.convertScaleAbs(img_bgr, alpha=(1.0 - dim), beta=0)

def bytes_of_file(p):
    try:
        return Path(p).read_bytes()
    except Exception:
        return None

def plot_hits_timeline(hit_times, height=300):
    if len(hit_times) == 0:
        return None, None
    tmax = float(max(hit_times))
    bins = np.arange(0.0, tmax + 1.01, 1.0)
    counts, edges = np.histogram(hit_times, bins=bins)
    xs = edges[:-1]
    ys = counts.astype(int)

    s = pd.Series(ys, dtype=float)
    smooth = s.rolling(window=3, center=True, min_periods=1).mean().to_numpy()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker=dict(color=ys, colorscale="Viridis", showscale=False),
            hovertemplate="t=%{x:.0f}–%{customdata:.0f}s<br>hits=%{y}<extra></extra>",
            customdata=(xs + 1.0),
            name="hits/s"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs + 0.5,
            y=smooth,
            mode="lines",
            line=dict(width=3),
            hovertemplate="t=%{x:.1f}s<br>rolling mean=%{y:.2f}<extra></extra>",
            name="rolling mean"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=np.array(hit_times, dtype=float),
            y=np.zeros((len(hit_times),), dtype=float) - 0.2,
            mode="markers",
            marker=dict(symbol="line-ns-open", size=10),
            hovertemplate="hit t=%{x:.2f}s<extra></extra>",
            name="hits"
        )
    )
    fig.update_layout(
        title="Hit intensity over time",
        xaxis_title="Time (sec)",
        yaxis_title="Hits per second",
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(range=[-0.5, max(1, int(max(ys)) + 1)])
    caption = f"Bars show hits per second (darker = higher). Line is a 3-bin rolling mean. Total hits={int(np.sum(ys))}, peak={int(np.max(ys))} hits/s."
    return fig, caption

def plot_hist_with_gradient(values, x_title, title, height=300, x_range=None, vlines=None, caption=None):
    values = np.array(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None, None
    if x_range is not None:
        lo, hi = x_range
        values = values[(values >= lo) & (values <= hi)]
        if values.size == 0:
            return None, None

    bins = 30
    counts, edges = np.histogram(values, bins=bins)
    xs = edges[:-1]
    widths = np.diff(edges)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=counts,
            width=widths,
            marker=dict(color=counts, colorscale="Viridis", showscale=False),
            hovertemplate=f"{x_title}=%{{x:.2f}}–%{{customdata:.2f}}<br>count=%{{y}}<extra></extra>",
            customdata=edges[1:],
            name="count"
        )
    )

    shapes = []
    ann = []
    if vlines:
        for lab, xv in vlines:
            try:
                xv = float(xv)
            except Exception:
                continue
            shapes.append(dict(type="line", x0=xv, x1=xv, y0=0, y1=max(1, int(np.max(counts))), xref="x", yref="y"))
            ann.append(dict(x=xv, y=max(1, int(np.max(counts))), xref="x", yref="y", text=str(lab), showarrow=True, arrowhead=2, ax=0, ay=-30))
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Count",
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        shapes=shapes,
        annotations=ann
    )
    if x_range is not None:
        fig.update_xaxes(range=[float(x_range[0]), float(x_range[1])])
    return fig, caption

def render(run_dir):
    run_dir = Path(run_dir)

    overlay = pick_first([
        run_dir / "viz" / "overlay_h264.mp4",
        run_dir / "viz" / "overlay.mp4",
        run_dir / "viz" / "overlay_raw.mp4",
        run_dir / "overlay_h264.mp4",
        run_dir / "overlay.mp4",
    ])

    meta = None
    if overlay:
        meta = open_video_meta(overlay)
    video_meta = load_json(run_dir / "video.json")
    if meta is None and isinstance(video_meta, dict):
        try:
            w = int(video_meta.get("width", 0))
            h = int(video_meta.get("height", 0))
            fps = float(video_meta.get("fps", 0) or 0)
            n = int(video_meta.get("frames", 0) or 0)
            if w > 0 and h > 0:
                meta = {"width": w, "height": h, "fps": (fps if fps > 0 else 30.0), "frames": n}
        except Exception:
            meta = None
    if meta is None:
        meta = {"width": 1920, "height": 1080, "fps": 30.0, "frames": 0}

    df, shuttle_path = load_shuttle_df(str(run_dir))
    if df is None:
        st.error("Cannot load shuttle CSV from run_dir. Expected tracks/shuttle.csv")
        st.stop()

    df_vis = df[(df["Visibility"] == 1) & np.isfinite(df["X"]) & np.isfinite(df["Y"])].copy()
    if len(df_vis) == 0:
        st.error("No visible points in shuttle CSV.")
        st.stop()

    fps = float(meta["fps"])

    max_gap_frames = 2
    accel_th = 2.0
    arrow_step = 40
    min_seg_len = 15
    dim = 0.35
    alpha = 0.95

    with st.expander("Settings", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            rally_gap_sec = st.slider("Rally gap (sec)", 0.1, 3.0, 0.8, 0.1)
            downsample = st.slider("Downsample", 1, 10, 1, 1)
        with col2:
            roi_str = st.text_input("ROI (x1,y1,x2,y2)", value="")
            max_speed_clean = st.slider("Max speed clean (px/frame)", 20.0, 300.0, 90.0, 5.0)
        with col3:
            mode = st.selectbox("Trajectory coloring", ["time", "speed", "segment"], index=0)
            thickness = st.slider("Line thickness", 1, 6, 2, 1)
        with col4:
            max_segs = st.slider("Max segments", 1, 30, 10, 1)
            hit_speed_th = st.slider("Hit speed threshold", 1.0, 80.0, 8.0, 0.5)

    rally_gap_frames = max(1, int(round(float(rally_gap_sec) * fps)))
    visible_frames = df_vis["Frame"].to_numpy(dtype=np.int32)
    rallies = segment_rallies_from_visible_frames(visible_frames, rally_gap_frames)

    rally_options = ["All"] + [f"Rally {i} ({r['start_frame']}–{r['end_frame']})" for i, r in enumerate(rallies)]
    sel = st.selectbox("Select rally", rally_options, index=0)
    sel_idx = None
    if sel != "All":
        sel_idx = int(sel.split()[1])

    if sel_idx is not None and 0 <= sel_idx < len(rallies):
        r = rallies[sel_idx]
        df_vis_sel = df_vis[(df_vis["Frame"] >= int(r["start_frame"])) & (df_vis["Frame"] <= int(r["end_frame"]))].copy()
        rallies_sel = [r]
    else:
        df_vis_sel = df_vis.copy()
        rallies_sel = rallies

    df_vis_sel = df_vis_sel.iloc[::max(1, int(downsample))].copy()
    roi = parse_roi(roi_str)

    fr = df_vis_sel["Frame"].to_numpy(dtype=np.int32)
    xy = df_vis_sel[["X", "Y"]].to_numpy(dtype=np.float32)
    segs, outlier_count = clean_and_segment(fr, xy, max_gap=int(max_gap_frames), max_speed=float(max_speed_clean), roi=roi)

    segs = [s for s in segs if len(s) >= int(min_seg_len)]
    segs.sort(key=lambda s: len(s), reverse=True)
    segs = segs[: int(max_segs)]
    segs.sort(key=lambda s: s[0][0] if len(s) else 0)

    events_calc = detect_hits(df_vis_sel, rallies_sel, fps=fps, hit_speed_th=float(hit_speed_th), accel_th=float(accel_th), max_gap_frames=int(max_gap_frames))

    total_frames_est = int(meta.get("frames", 0) or 0)
    if total_frames_est <= 0:
        total_frames_est = int(df["Frame"].max()) + 1

    coverage = float(len(df_vis)) / float(max(1, total_frames_est))
    avg_gap_sec, gap_count = compute_gaps_seconds(df_vis["Frame"].to_numpy(dtype=np.int32), fps)

    num_rallies = len(rallies_sel) if sel_idx is not None else len(rallies)
    total_hits = len([e for e in events_calc if e.get("type") == "hit"])
    if len(rallies_sel) > 0:
        durs = [(int(r["end_frame"]) - int(r["start_frame"]) + 1) / fps for r in rallies_sel]
        avg_rally = float(np.mean(durs))
    else:
        avg_rally = 0.0

    sp = [float(e["speed"]) for e in events_calc if e.get("type") == "hit" and "speed" in e]
    avg_speed = float(np.mean(sp)) if len(sp) > 0 else 0.0

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Rallies", str(num_rallies))
    c2.metric("Total hits", str(total_hits))
    c3.metric("Avg rally (sec)", f"{avg_rally:.2f}")
    c4.metric("Avg speed", f"{avg_speed:.2f}" if len(sp) else "-")
    c5.metric("Coverage", f"{coverage*100:.1f}%")
    c6.metric("Outliers filtered", str(outlier_count))
    c7.metric("Avg gap (sec)", f"{avg_gap_sec:.2f}" if gap_count else "-")

    st.caption(f"points_used={len(df_vis_sel)}  segs_drawn={len(segs)}  downsample={downsample}, max_speed_clean={max_speed_clean}, max_segs={max_segs}, thickness={thickness}, mode={mode}")

    left, right = st.columns(2)

    with left:
        st.subheader("Trajectory Plot")
        bg = None
        if overlay:
            bg = read_mid_frame(str(overlay))
        if bg is None:
            bg = np.zeros((int(meta["height"]), int(meta["width"]), 3), dtype=np.uint8)

        bg = dim_background(bg, float(dim))
        traj_overlay = render_trajectory_overlay(bg, segs, mode=mode, thickness=int(thickness), arrow_step=int(arrow_step))
        out = cv2.addWeighted(bg, 1.0, traj_overlay, float(alpha), 0.0)

        if roi is not None:
            x1, y1, x2, y2 = roi
            cv2.rectangle(out, (x1, y1), (x2, y2), (255, 255, 255), 2)

        out_rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
        st.image(out_rgb, width="stretch")

        ok, enc = cv2.imencode(".png", out_rgb)
        if ok:
            st.download_button("Download trajectory plot (PNG)", data=enc.tobytes(), file_name="trajectory_plot.png", mime="image/png")

    with right:
        st.subheader("Overlay")
        if overlay:
            st.video(str(overlay))
        else:
            st.warning("No overlay video found in viz/")

    st.subheader("Event timeline (hits)")
    hit_times = [float(e["time_sec"]) for e in events_calc if e.get("type") == "hit" and "time_sec" in e]
    fig_tl, cap_tl = plot_hits_timeline(hit_times, height=300) if len(hit_times) else (None, None)
    if fig_tl is not None:
        st.plotly_chart(fig_tl, use_container_width=True)
        st.caption(cap_tl)
    else:
        st.write("No hits detected with current thresholds.")

    spd = []
    if len(df_vis_sel) > 2:
        frs = df_vis_sel["Frame"].to_numpy(dtype=np.int32)
        xs = df_vis_sel["X"].to_numpy(dtype=np.float32)
        ys = df_vis_sel["Y"].to_numpy(dtype=np.float32)
        for i in range(1, len(frs)):
            dt = int(frs[i] - frs[i - 1])
            if dt <= 0 or dt > int(max_gap_frames):
                continue
            spd.append(math.hypot(float(xs[i] - xs[i - 1]), float(ys[i] - ys[i - 1])) / float(dt))

    st.subheader("Distributions")
    tab1, tab2 = st.tabs(["Speed", "Y position"])

    with tab1:
        if len(spd) > 0:
            spd_arr = np.array(spd, dtype=float)
            spd_arr = spd_arr[np.isfinite(spd_arr)]
            p50 = float(np.percentile(spd_arr, 50))
            p90 = float(np.percentile(spd_arr, 90))
            p95 = float(np.percentile(spd_arr, 95))
            p99 = float(np.percentile(spd_arr, 99))
            vmax = float(np.max(spd_arr))
            xmax = p95
            fig_h, cap_h = plot_hist_with_gradient(
                spd_arr,
                x_title="Speed (px/frame)",
                title="Speed distribution",
                height=300,
                x_range=(0.0, xmax),
                vlines=[("P50", p50), ("P90", p90), ("P95", p95)],
                caption=f"Histogram is clipped to P95 for readability (max shown={p95:.2f}). True max={vmax:.2f}. P50={p50:.2f}, P90={p90:.2f}, P99={p99:.2f}."
            )
            if fig_h is not None:
                st.plotly_chart(fig_h, use_container_width=True)
                st.caption(cap_h)
        else:
            st.write("Not enough points to compute speed distribution.")

    with tab2:
        yv = df_vis_sel["Y"].to_numpy(dtype=float)
        yv = yv[np.isfinite(yv)]
        if yv.size > 0:
            ymean = float(np.mean(yv))
            p10 = float(np.percentile(yv, 10))
            p90 = float(np.percentile(yv, 90))
            fig_y, cap_y = plot_hist_with_gradient(
                yv,
                x_title="Y (px)",
                title="Y-position distribution",
                height=300,
                x_range=None,
                vlines=[("Mean", ymean), ("P10", p10), ("P90", p90)],
                caption=f"Y is image-plane vertical coordinate (px). Lower Y means higher on screen. Mean={ymean:.1f}, P10={p10:.1f}, P90={p90:.1f}."
            )
            if fig_y is not None:
                st.plotly_chart(fig_y, use_container_width=True)
                st.caption(cap_y)
        else:
            st.write("No Y values available.")

    st.subheader("Events")
    if len(events_calc) > 0:
        df_events = pd.DataFrame(events_calc)
        st.dataframe(df_events, use_container_width=True)
        csv_bytes = df_events.to_csv(index=False).encode("utf-8")
        st.download_button("Download events.csv", data=csv_bytes, file_name="events.csv", mime="text/csv")
    else:
        st.write("No events")

    st.subheader("Exports")
    colE1, colE2, colE3 = st.columns(3)

    with colE1:
        if shuttle_path and Path(shuttle_path).exists():
            st.download_button("Download shuttle.csv", data=Path(shuttle_path).read_bytes(), file_name="shuttle.csv", mime="text/csv")

    with colE2:
        metrics_obj = {
            "summary": {
                "num_rallies": int(num_rallies),
                "total_hits": int(total_hits),
                "avg_rally_seconds": float(avg_rally),
                "avg_hit_speed": (float(avg_speed) if len(sp) else None),
                "coverage": float(coverage),
                "outliers_filtered": int(outlier_count),
                "avg_gap_seconds": (float(avg_gap_sec) if gap_count else None)
            },
            "params": {
                "rally_gap_sec": float(rally_gap_sec),
                "rally_gap_frames": int(rally_gap_frames),
                "downsample": int(downsample),
                "roi": (roi_str if roi_str else None),
                "max_speed_clean": float(max_speed_clean),
                "max_gap_frames": int(max_gap_frames),
                "min_seg_len": int(min_seg_len),
                "max_segs": int(max_segs),
                "mode": str(mode),
                "thickness": int(thickness),
                "arrow_step": int(arrow_step),
                "dim": float(dim),
                "alpha": float(alpha),
                "hit_speed_th": float(hit_speed_th),
                "accel_th": float(accel_th)
            },
            "data": {
                "run_dir": str(run_dir),
                "overlay": (str(overlay) if overlay else None),
                "shuttle_csv": shuttle_path,
            }
        }
        st.download_button("Download metrics.json", data=json.dumps(metrics_obj, indent=2).encode("utf-8"), file_name="metrics.json", mime="application/json")

    with colE3:
        if overlay and overlay.exists():
            b = bytes_of_file(overlay)
            if b:
                st.download_button("Download overlay.mp4", data=b, file_name=overlay.name, mime="video/mp4")

    with st.expander("Data sources", expanded=False):
        st.write({
            "run_dir": str(run_dir),
            "overlay": (str(overlay) if overlay else None),
            "shuttle_csv": shuttle_path,
            "rows_total": int(len(df)),
            "rows_visible": int(len(df_vis)),
            "frame_min": int(df["Frame"].min()),
            "frame_max": int(df["Frame"].max()),
            "video_meta": meta
        })

def main(run_dir):
    st.set_page_config(page_title="Badminton Performance Analyzer", layout="wide")
    st.title("Badminton Performance Analyzer")
    render(run_dir)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run_dir", required=True)
    args = p.parse_args()
    main(args.run_dir)