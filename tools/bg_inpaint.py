"""首幀背景對齊實景：人物遮罩保留＋只重畫背景（2026-10-23《團結》第 3 階段實驗，採用）。

為什麼：H3 的背景完全由首幀決定（改 H3 場景描述改不動），所以背景不像實景只能修首幀。
qwen-edit 直接換背景會跟著照片視角重新構圖、甚至換臉（《團結》教室近景 3 鏡失敗）→ 改成：
  1) rembg 摳出人物遮罩（facecheck venv）
  2) Qwen-Image 2.1 只在背景區重繪（DifferentialDiffusion，實景照當參考圖 <image1>，遮罩外擴 6px＋羽化 8px）
  3) 人物區用原圖像素貼回（臉 100% 不變）→ 背景高斯模糊做淺景深
每張約 75 秒（RTX 5060 Ti 16GB）。

film.json 設定（放在影片資料夾，與 out/ 同層）：
  "bg_inpaint": {
    "scenes": {"<scene 鍵>": {"photo": "實景照路徑（相對 film.json）", "prompt": "背景描述，要寫 <image1>"}},
    "negative": "low quality, watermark, text, numbers, sign, plaque",
    "blur": 2.5
  }
  單鏡可加 "bg_mask": "people"（背景同學也要保留：u2net_human_seg）或 "object"（手部／道具特寫：birefnet-general，不模糊）；
  不寫＝birefnet-portrait（單人）。單鏡也可寫 "bg_scene" 指定用哪個 scenes 鍵（預設＝shot.scene[0]）。

用法（H3 venv 的 python，ComfyUI 要開著）：
  bg_inpaint.py <鏡,...> [--dir 影片資料夾] [--seeds 2] [--seed-base 4400]
  → out/bg_inpaint/<鏡>_s<seed>.png（遮罩存 out/bg_inpaint/mask_<鏡>.png，bgcheck.py --masks 可直接用）
挑好後手動複製成 out/first/<鏡>.png（原檔先備份）。

注意：提示詞與負面詞要寫 no signs/plaques——實景照裡的班級牌會被畫出來；人物光線仍是原首幀的光，與背景可能略有落差。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comfy_util import QWEN21, run_graph, to_input  # noqa: E402

FACEPY = os.environ.get("PY_FACECHECK", r"D:\AI\facecheck\venv\Scripts\python.exe")   # 裝了 rembg 的環境
MASK_MODEL = {"people": "u2net_human_seg", "object": "birefnet-general"}


def make_mask(first, dst, kind):
    if dst.exists():
        return
    model = MASK_MODEL.get(kind, "birefnet-portrait")
    code = ("from rembg import remove,new_session;from PIL import Image;import sys;"
            "s=new_session(sys.argv[3]);remove(Image.open(sys.argv[1]).convert('RGB'),session=s,only_mask=True).save(sys.argv[2])")
    subprocess.run([FACEPY, "-c", code, str(first), str(dst), model], check=True)


def blur_bg(path, mask, radius):
    """背景微模糊（淺景深感、藏接縫）：人物區保持原清晰度"""
    from PIL import Image, ImageFilter
    im = Image.open(path).convert("RGB")
    mk = Image.open(mask).convert("L").resize(im.size).filter(ImageFilter.GaussianBlur(3))
    Image.composite(im, im.filter(ImageFilter.GaussianBlur(radius)), mk).save(path)


def graph(img, msk, photo, prompt, negative, seed, prefix):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": QWEN21["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN21["clip"], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN21["vae"]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": img}},
        "12": {"class_type": "LoadImage", "inputs": {"image": msk}},
        "13": {"class_type": "ImageToMask", "inputs": {"image": ["12", 0], "channel": "red"}},
        "14": {"class_type": "InvertMask", "inputs": {"mask": ["13", 0]}},                        # 背景＝1、人物＝0
        "15": {"class_type": "GrowMask", "inputs": {"mask": ["14", 0], "expand": 6, "tapered_corners": True}},   # 往人物邊緣吃 6px，接縫自然
        "16": {"class_type": "FeatherMask", "inputs": {"mask": ["15", 0], "left": 8, "top": 8, "right": 8, "bottom": 8}},
        "17": {"class_type": "LoadImage", "inputs": {"image": photo}},
        "20": {"class_type": "VAEEncode", "inputs": {"pixels": ["11", 0], "vae": ["3", 0]}},
        "21": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["20", 0], "mask": ["16", 0]}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": negative,
                                                               "resolution": 1024, "images.image_1": ["17", 0]}},
        "25": {"class_type": "DifferentialDiffusion", "inputs": {"model": ["1", 0]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["25", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["21", 0],
                                                   "seed": seed, "steps": 50, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "31": {"class_type": "InvertMask", "inputs": {"mask": ["16", 0]}},
        # 人物區用原圖像素貼回（保證臉一模一樣）
        "30": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["7", 0], "source": ["11", 0], "x": 0, "y": 0,
                                                              "resize_source": False, "mask": ["31", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["30", 0], "filename_prefix": prefix}},
    }


def main():
    ap = argparse.ArgumentParser(description="首幀背景重繪成實景（人物不動）")
    ap.add_argument("shots"); ap.add_argument("--dir", default=".", help="影片資料夾（有 film.json 與 out/）")
    ap.add_argument("--seeds", type=int, default=2); ap.add_argument("--seed-base", type=int, default=4400)
    a = ap.parse_args()
    here = Path(a.dir).resolve(); cfg = json.loads((here / "film.json").read_text(encoding="utf-8"))
    bi = cfg["bg_inpaint"]; shots = {s["id"]: s for s in cfg["shots"]}
    out = here / "out" / "bg_inpaint"; out.mkdir(parents=True, exist_ok=True)
    for sid in a.shots.split(","):
        s = shots[sid]; key = s.get("bg_scene") or (s.get("scene") or [None])[0]
        sc = bi["scenes"][key]; first = here / "out" / "first" / f"{sid}.png"; m = out / f"mask_{sid}.png"
        make_mask(first, m, s.get("bg_mask"))
        img = to_input(first, f"bgi_{sid}.png"); msk = to_input(m, f"bgi_mask_{sid}.png")
        photo = to_input((here / sc["photo"]).resolve(), f"bgi_photo_{key}{Path(sc['photo']).suffix}")
        for k in range(a.seeds):
            seed = a.seed_base + k; dst = out / f"{sid}_s{seed}.png"
            if dst.exists():
                continue
            g = graph(img, msk, photo, sc["prompt"], bi.get("negative", "low quality, watermark, text, numbers, sign, plaque"), seed, f"bgi/{sid}_s{seed}")
            if run_graph(g, dst, f"{sid} s{seed}") and s.get("bg_mask") != "object":
                blur_bg(dst, m, bi.get("blur", 2.5))


if __name__ == "__main__":
    main()
