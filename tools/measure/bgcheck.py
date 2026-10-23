# 背景一致性量測（2026-10-23）：遮掉人物後，用 DINOv2 的「場景特徵」比較背景
# 做法參考 VBench background/subject consistency（逐格特徵 cosine），但改成：只取「沒有人」的區塊、可對照實景照片、可跨鏡頭
# 三種用法：
#   ref    ：每張圖的背景 vs 實景照片（哪張最像、分數多少）
#            bgcheck.py ref --images out/first/*.png --refs 教室.jpg 走廊.jpg --masks out/bg_inpaint --out 結果資料夾
#   matrix ：同一場景的鏡頭兩兩比對，找出「背景長得不一樣」的那鏡
#            bgcheck.py matrix --images S03.png S06.png ... --masks ... --out ...
#   video  ：一支影片每一格的背景 vs 第一格（抓 H3 偷換場景、鏡頭推近）
#            bgcheck.py video --videos a.mp4 b.mp4 --out ...
# 人物遮罩：--masks 資料夾裡有 mask_<檔名>.png 就用它；沒有就用 rembg（birefnet-portrait）自動算並存下來
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel

GW, GH = 37, 21                       # DINOv2 patch 14 → 518×294（16:9，不裁邊）
MEAN = np.array([0.485, 0.456, 0.406]); STD = np.array([0.229, 0.224, 0.225])
_model = None; _rembg = None


def model():
    global _model
    if _model is None:
        _model = AutoModel.from_pretrained("facebook/dinov2-base").eval()
    return _model


def fit169(im):
    """裁成 16:9（直拍照片取中段），再縮到 518×294"""
    w, h = im.size; tw = w; th = int(w * 9 / 16)
    if th > h:
        th = h; tw = int(h * 16 / 9)
    x0 = (w - tw) // 2; y0 = (h - th) // 2
    return im.crop((x0, y0, x0 + tw, y0 + th)).resize((GW * 14, GH * 14), Image.BICUBIC)


def person_mask(img, path, mask_dir):
    """回傳 GH×GW 的「背景」權重（1＝背景、0＝人物）"""
    m = None
    if mask_dir:
        cand = Path(mask_dir) / f"mask_{Path(path).stem}.png"
        if cand.exists():
            m = Image.open(cand).convert("L")
        else:
            global _rembg
            from rembg import remove, new_session
            _rembg = _rembg or new_session("birefnet-portrait")
            m = remove(img, session=_rembg, only_mask=True); m.save(cand)
    if m is None:
        return np.ones((GH, GW))
    a = np.asarray(fit169(m).resize((GW, GH), Image.BOX), float) / 255.0
    return (a < 0.1).astype(float)    # 只要格子裡有一點人就排除


@torch.no_grad()
def feat(img, bgw=None):
    """背景特徵：背景格子的 patch 特徵平均（L2 正規化）"""
    x = (np.asarray(fit169(img.convert("RGB")), float) / 255.0 - MEAN) / STD
    x = torch.tensor(x.transpose(2, 0, 1)[None], dtype=torch.float32)
    tok = model()(pixel_values=x).last_hidden_state[0, 1:]          # (GH*GW, 768)
    tok = torch.nn.functional.normalize(tok, dim=-1).numpy()
    w = np.ones(GH * GW) if bgw is None else bgw.reshape(-1)
    if w.sum() < 10:                                                  # 背景太少（大特寫）就退回整張
        w = np.ones(GH * GW)
    v = (tok * w[:, None]).sum(0); return v / np.linalg.norm(v), float(w.mean())


def load_imgs(pats):
    out = []
    for p in pats:
        out += sorted(glob.glob(p)) if any(c in p for c in "*?") else [p]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["ref", "matrix", "video"])
    ap.add_argument("--images", nargs="*", default=[]); ap.add_argument("--refs", nargs="*", default=[])
    ap.add_argument("--videos", nargs="*", default=[]); ap.add_argument("--masks"); ap.add_argument("--fps", type=float, default=2)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Microsoft JhengHei"

    if a.mode in ("ref", "matrix"):
        paths = load_imgs(a.images); res = {}
        F = {}
        for p in paths:
            im = Image.open(p).convert("RGB"); bg = person_mask(im, p, a.masks)
            F[p], cover = feat(im, bg); res[Path(p).stem] = {"背景比例": round(cover, 2)}
        if a.mode == "ref":
            R = {Path(r).stem: feat(Image.open(r))[0] for r in a.refs}
            for p in paths:
                s = {k: round(float(F[p] @ v), 3) for k, v in R.items()}
                res[Path(p).stem].update(s, 最像=max(s, key=s.get))
                print(Path(p).stem, res[Path(p).stem], flush=True)
        else:
            names = [Path(p).stem for p in paths]; M = np.array([[F[p] @ F[q] for q in paths] for p in paths])
            for i, n in enumerate(names):
                res[n]["與其他鏡平均"] = round(float((M[i].sum() - 1) / max(1, len(paths) - 1)), 3)
                print(n, res[n], flush=True)
            plt.figure(figsize=(1 + len(names) * 0.45, 1 + len(names) * 0.45))
            plt.imshow(M, vmin=0.3, vmax=1, cmap="viridis"); plt.colorbar()
            plt.xticks(range(len(names)), names, rotation=90, fontsize=7); plt.yticks(range(len(names)), names, fontsize=7)
            plt.title("背景相似度（遮人物後）"); plt.tight_layout(); plt.savefig(out / "matrix.png", dpi=110); plt.close()
        (out / f"{a.mode}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    else:  # video：每一格背景 vs 第一格（遮罩用第一格的人物位置，人物移動時會有小誤差）
        import cv2
        res = {}
        for v in a.videos:
            cap = cv2.VideoCapture(v); vfps = cap.get(cv2.CAP_PROP_FPS) or 24; step = max(1, round(vfps / a.fps))
            t, s, i, f0, bg = [], [], 0, None, None
            while True:
                ok, fr = cap.read()
                if not ok:
                    break
                if i % step == 0:
                    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                    if f0 is None:
                        bg = person_mask(im, str(Path(v).parent / (Path(v).parent.name + "_frame0.png")), a.masks or str(out))
                        f0, _ = feat(im, bg)
                    f, _ = feat(im, bg); t.append(i / vfps); s.append(float(f @ f0))
                i += 1
            name = Path(v).parent.name; res[name] = {"最低": round(min(s), 3), "結尾": round(s[-1], 3)}
            print(name, res[name], flush=True)
            plt.figure(figsize=(7, 2.6)); plt.plot(t, s); plt.ylim(0.5, 1); plt.xlabel("秒"); plt.ylabel("背景 vs 第一格")
            plt.title(name); plt.tight_layout(); plt.savefig(out / f"video_{name}.png", dpi=90); plt.close()
        (out / "video.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
