import argparse
import json
from pathlib import Path

import cv2
import numpy as np

state = {"pts": []}

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(state["pts"]) < 4:
            state["pts"].append((float(x), float(y)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", type=int, default=-1)
    ap.add_argument("--court_w", type=int, default=610)
    ap.add_argument("--court_h", type=int, default=1340)
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {args.video}")

    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    idx = args.frame
    if idx < 0:
        idx = max(0, n // 2)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("Failed to read frame")

    win = "Calibrate Court (click 4 corners: TL, TR, BR, BL) | q=quit | r=reset | s=save"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, on_mouse)

    while True:
        vis = frame.copy()
        txt = [
            "Click 4 court outer corners (doubles):",
            "1) Top-Left  2) Top-Right  3) Bottom-Right  4) Bottom-Left",
            "Keys: r=reset, s=save (after 4 pts), q=quit"
        ]
        y0 = 30
        for t in txt:
            cv2.putText(vis, t, (20, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            y0 += 30

        for i, (x, y) in enumerate(state["pts"]):
            cv2.circle(vis, (int(x), int(y)), 7, (0, 0, 255), -1)
            cv2.putText(vis, str(i + 1), (int(x) + 10, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        cv2.imshow(win, vis)
        k = cv2.waitKey(20) & 0xFF

        if k == ord("q"):
            break
        if k == ord("r"):
            state["pts"] = []
        if k == ord("s"):
            if len(state["pts"]) != 4:
                continue
            src = np.array(state["pts"], dtype=np.float32)
            W, H = int(args.court_w), int(args.court_h)
            dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
            Hm, _ = cv2.findHomography(src, dst, method=0)
            if Hm is None:
                continue
            out = {
                "court_size": [W, H],
                "src_pts": src.tolist(),
                "H": Hm.tolist()
            }
            p = Path(args.out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(out, indent=2), encoding="utf-8")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()