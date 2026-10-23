# 臉部相似度逐格檢查（2026-10-23）：影片每一格的臉 vs 首幀的臉，量化「換臉／臉部漂移」
# 找臉：OpenCV YuNet；比對：OpenCV SFace（cosine 相似度，官方門檻 0.363 以上視為同一人）
# 用法：facecheck.py <首幀.png> <影片.mp4> [<影片2.mp4> ...] --out <結果資料夾> [--fps 6]
# 輸出：每支影片一張曲線圖＋summary.json（每個人：最低相似度、低於門檻的秒數、平均）
import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = Path(os.environ.get("FACECHECK_MODELS", HERE / "models"))   # 模型資料夾：預設與本檔同層的 models/
DET = str(MODELS / "face_detection_yunet_2023mar.onnx")
REC = str(MODELS / "face_recognition_sface_2021dec.onnx")
SAME = 0.363   # SFace 官方建議的 cosine 同一人門檻


def faces(img, det, rec):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, fs = det.detect(img)
    out = []
    for f in (fs if fs is not None else []):
        if f[-1] < 0.8 or f[2] * f[3] < 40 * 40:          # 信心不足或臉太小（遠景）就跳過
            continue
        feat = rec.feature(rec.alignCrop(img, f))
        out.append((float(f[0] + f[2] / 2), feat))          # (臉中心 x, 特徵)
    return sorted(out, key=lambda t: t[0])                  # 由左到右排序，對應首幀的人


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("first"); ap.add_argument("videos", nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=6.0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    det = cv2.FaceDetectorYN.create(DET, "", (320, 320), 0.8)
    rec = cv2.FaceRecognizerSF.create(REC, "")
    ref = faces(cv2.imread(a.first), det, rec)
    if not ref:
        raise SystemExit("首幀找不到臉")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    summary = {}
    for v in a.videos:
        cap = cv2.VideoCapture(v); vfps = cap.get(cv2.CAP_PROP_FPS) or 24; step = max(1, round(vfps / a.fps))
        t, curves, i = [], [[] for _ in ref], 0
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            if i % step == 0:
                fs = faces(fr, det, rec); t.append(i / vfps)
                for k, (_, rf) in enumerate(ref):
                    # 每個首幀的人，取這一格裡最像他的那張臉
                    s = max((rec.match(rf, ff, cv2.FaceRecognizerSF_FR_COSINE) for _, ff in fs), default=np.nan)
                    curves[k].append(s)
            i += 1
        name = Path(v).parent.name + "_" + Path(v).stem
        res = {}
        for k, c in enumerate(curves):
            c = np.array(c, float); valid = c[~np.isnan(c)]
            res[f"人{k + 1}"] = dict(min=round(float(valid.min()), 3) if len(valid) else None,
                                    mean=round(float(valid.mean()), 3) if len(valid) else None,
                                    低於門檻秒數=round(float(np.sum(valid < SAME)) * step / vfps, 2),
                                    找不到臉比例=round(float(np.mean(np.isnan(c))), 2))
        summary[v] = res
        plt.figure(figsize=(8, 3))
        for k, c in enumerate(curves):
            plt.plot(t, c, label=f"face {k + 1}")
        plt.axhline(SAME, color="r", ls="--", lw=1); plt.ylim(0, 1); plt.xlabel("sec"); plt.ylabel("cosine vs first frame")
        plt.title(name); plt.legend(); plt.tight_layout(); plt.savefig(out / f"{name}.png", dpi=90); plt.close()
        print(name, json.dumps(res, ensure_ascii=False), flush=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
