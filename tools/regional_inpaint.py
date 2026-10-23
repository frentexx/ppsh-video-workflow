"""同畫面多角色 LoRA：分區重繪（2026-10-23《團結》實驗三，採用）。

問題：兩人同框直接掛角色 LoRA，LoRA 會「外溢」到每個人身上（另一人也長成同一張臉）。
ComfyUI 內建 hook 區域 LoRA 不支援 int8 壓縮版 Qwen-Image（'Linear' object has no attribute 'weight_scale'），
未壓縮版約 40GB，16GB 顯卡放不下 → 改成「切割畫面、分次重畫，每次只掛一顆 LoRA」：
  底圖（不掛 LoRA，只靠文字把構圖、動作做對）→ 遮右半、掛 A 的 LoRA 重畫 → 遮左半、掛 B 的 LoRA 重畫
每多一個角色多一次重繪（約 1 分鐘）。

前提：兩人在畫面上分得開（各占一邊）。重疊、交錯時改用 --mask 給人形遮罩（白＝要重畫）。
重畫強度 0.75：太低換不了臉，太高會跟另一半接不起來、背景也會跑。

用法（H3 venv 的 python，ComfyUI 要開著）：
  regional_inpaint.py --base 底圖.png --region R --lora datou_tw.safetensors --prompt "The person on the RIGHT is datou_tw, ..." \
                      --scene "整張畫面的共用描述" --seed 801 --out 右重畫.png
  regional_inpaint.py --base 右重畫.png --region L --lora cai_tw.safetensors --prompt "The person on the LEFT is cai_tw, ..." --out 完成.png
--region：L（左半）、R（右半）、或 0.55,1.0（畫面寬度比例的起訖）；或改用 --mask 遮罩.png。
提示詞要同時有「觸發詞＋外觀描述」，並寫明是 LEFT／RIGHT 那個人。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comfy_util import QWEN21, run_graph, to_input  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="分區重繪：一次只掛一顆角色 LoRA，只重畫畫面的一塊")
    ap.add_argument("--base", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--lora", required=True); ap.add_argument("--lora-strength", type=float, default=1.0)
    ap.add_argument("--prompt", required=True, help="這一區的人物描述（觸發詞＋外觀）")
    ap.add_argument("--scene", default="", help="整張畫面的共用描述（場景、光線），放在提示詞前面")
    ap.add_argument("--region", default="R"); ap.add_argument("--mask", help="自訂遮罩圖（白＝重畫），有給就忽略 --region")
    ap.add_argument("--denoise", type=float, default=0.75); ap.add_argument("--feather", type=int, default=80)
    ap.add_argument("--seed", type=int, default=801)
    ap.add_argument("--negative", default="blurry, low quality, extra limbs, watermark, text")
    a = ap.parse_args()

    from PIL import Image
    W, H = Image.open(a.base).size
    img = to_input(a.base, "rgn_" + Path(a.base).name)
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": QWEN21["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN21["clip"], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN21["vae"]}},
        "9": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": a.lora, "strength_model": a.lora_strength}},
        "11": {"class_type": "LoadImage", "inputs": {"image": img}},
        "12": {"class_type": "VAEEncode", "inputs": {"pixels": ["11", 0], "vae": ["3", 0]}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": (a.scene + " " + a.prompt).strip(),
                                                               "negative_prompt": a.negative, "resolution": 1024}},
        "25": {"class_type": "DifferentialDiffusion", "inputs": {"model": ["9", 0]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["25", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["24", 0],
                                                   "seed": a.seed, "steps": 50, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                                                   "denoise": a.denoise}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "regional/" + Path(a.out).stem}},
    }
    if a.mask:   # 人形遮罩：白＝重畫
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": to_input(a.mask, "rgn_mask_" + Path(a.mask).name)}}
        g["21"] = {"class_type": "ImageToMask", "inputs": {"image": ["20", 0], "channel": "red"}}
        g["23"] = {"class_type": "FeatherMask", "inputs": {"mask": ["21", 0], "left": 16, "top": 16, "right": 16, "bottom": 16}}
    else:        # 左右切：要重畫的那一塊＝1，靠另一邊的邊緣羽化，讓接縫自然
        r = {"L": (0.0, 0.5), "R": (0.5, 1.0)}.get(a.region.upper()) or tuple(float(x) for x in a.region.split(","))
        x0, x1 = int(r[0] * W), int(r[1] * W)
        g["20"] = {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": W, "height": H}}
        g["21"] = {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": x1 - x0, "height": H}}
        g["22"] = {"class_type": "MaskComposite", "inputs": {"destination": ["20", 0], "source": ["21", 0], "x": x0, "y": 0, "operation": "add"}}
        g["23"] = {"class_type": "FeatherMask", "inputs": {"mask": ["22", 0], "left": a.feather if x0 > 0 else 0, "top": 0,
                                                           "right": a.feather if x1 < W else 0, "bottom": 0}}
    g["24"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["12", 0], "mask": ["23", 0]}}
    run_graph(g, a.out, Path(a.out).name)


if __name__ == "__main__":
    main()
