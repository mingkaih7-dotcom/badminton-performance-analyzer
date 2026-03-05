import numpy as np

def segment_rallies(shuttle_df, cfg):
    min_visible = int(cfg["rally"].get("min_visible_frames", 30))
    gap_th = int(cfg["rally"].get("gap_threshold_frames", 45))
    min_rally = int(cfg["rally"].get("min_rally_frames", 60))

    vis = shuttle_df["Visibility"].to_numpy()
    frames = shuttle_df["Frame"].to_numpy()

    visible_idx = np.where(vis == 1)[0]
    if visible_idx.size == 0:
        return []

    runs = []
    start_i = visible_idx[0]
    prev_i = visible_idx[0]
    for i in visible_idx[1:]:
        if frames[i] - frames[prev_i] > gap_th:
            runs.append((start_i, prev_i))
            start_i = i
        prev_i = i
    runs.append((start_i, prev_i))

    rallies = []
    for s, e in runs:
        if e - s + 1 < min_visible:
            continue
        start_frame = int(frames[s])
        end_frame = int(frames[e])
        if end_frame - start_frame + 1 < min_rally:
            continue
        rallies.append({"start_frame": start_frame, "end_frame": end_frame})
    return rallies
