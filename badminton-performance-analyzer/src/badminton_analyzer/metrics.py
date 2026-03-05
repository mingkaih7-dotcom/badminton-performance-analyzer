def compute_metrics(video_meta, rallies, events):
    fps = float(video_meta.get("fps", 30.0))
    hit_counts = {}
    for e in events:
        if e.get("type") != "hit":
            continue
        ri = int(e.get("rally_index", -1))
        hit_counts[ri] = hit_counts.get(ri, 0) + 1

    rally_metrics = []
    for i, r in enumerate(rallies):
        dur_frames = r["end_frame"] - r["start_frame"] + 1
        dur_sec = dur_frames / fps if fps > 0 else 0.0
        rally_metrics.append({
            "rally_index": i,
            "start_frame": r["start_frame"],
            "end_frame": r["end_frame"],
            "duration_frames": dur_frames,
            "duration_seconds": dur_sec,
            "hit_count": hit_counts.get(i, 0)
        })

    summary = {
        "num_rallies": len(rallies),
        "total_hits": sum(hit_counts.values()),
        "avg_rally_seconds": (sum([m["duration_seconds"] for m in rally_metrics]) / len(rally_metrics)) if rally_metrics else 0.0
    }

    return {"summary": summary, "rallies": rally_metrics}
