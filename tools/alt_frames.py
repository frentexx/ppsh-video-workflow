"""首幀的另外三種做法（make_film.py frames 不適合時用；2026-10-22～23《團結》第 2 版整理）。

make_film.py 的預設首幀＝qwen-edit 附「角色定妝照＋場景裁切」。以下情況會失敗，改用本工具：
  photo ：遠景多人鏡。定妝照×2＋場景的組法會丟掉場景與動作（《團結》N1 變兩人自拍）
          → 只給一張實景照當 <image1>，請 qwen-edit「在照片上加人」，外觀靠文字描述（遠景臉小，認不出來也沒關係）
  lora  ：有角色 LoRA 的單人近景。qwen21＋角色 LoRA、不給場景參考圖，長相最一致
          （兩人同框不要用：LoRA 會外溢成雙胞胎 → 用 photo 做構圖，再 edit_fix.py 換臉或 regional_inpaint.py 分區重繪）
  chars ：沒有 LoRA 的角色。同 make_film frames 的組法，但一次出多張候選給人挑

film.json 單鏡設定（"alt" 欄位）：
  "alt": {"method": "photo", "prompt": "Edit <image1>: keep this exact school corridor photo unchanged ... Add exactly two ...",
          "photo": "masters/crop_N1.png"}          ← photo：相對於 out/；不寫＝out/masters/crop_<鏡>.png
  "alt": {"method": "lora", "prompt": "Chest-up medium close-up ... {CORRIDOR} ...", "lora": "datou_tw.safetensors:1.0", "char": "gou"}
          ← 提示詞前面會自動接上 chars.<char>.lora_prompt（觸發詞＋外觀），沒有就用 look
  "alt": {"method": "chars"}                        ← 用該鏡的 refs、frame 與全片 cine／set_sentence／frame_suffix
提示詞可用 {名稱} 引用 film.json 的 "snippets"（例如固定的走廊方向描述），避免每鏡複製貼上、改一處漏一處。

用法（H3 venv 的 python，ComfyUI 要開著）：
  alt_frames.py <鏡> [<鏡> ...] [--dir 影片資料夾] [--n 4] [--start 1] [--seed-base 9100]
  → out/alt/<鏡>_e<k>_00001_.png；挑好後手動複製成 out/first/<鏡>.png，並在 film.json 該鏡寫 frame_method 註明做法
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

PY = os.environ.get("PY_H3", r"C:\AI\H3\venv\Scripts\python.exe")
GEN = Path(os.environ.get("AI_TOOLS", r"C:\AI\tools")) / "gen_image.py"


def fill(text, snippets):
    for k, v in snippets.items():
        text = text.replace("{" + k + "}", v)
    return text


def main():
    ap = argparse.ArgumentParser(description="首幀另外三種做法：photo／lora／chars")
    ap.add_argument("shots", nargs="+"); ap.add_argument("--dir", default=".")
    ap.add_argument("--n", type=int, default=4, help="每鏡候選數"); ap.add_argument("--start", type=int, default=1, help="重抽時從第幾號開始")
    ap.add_argument("--seed-base", type=int, default=9100)
    a = ap.parse_args()
    here = Path(a.dir).resolve(); cfg = json.loads((here / "film.json").read_text(encoding="utf-8"))
    out = here / "out"; alt = out / "alt"; alt.mkdir(parents=True, exist_ok=True)
    shots = {s["id"]: s for s in cfg["shots"]}; chars = cfg["chars"]; snip = cfg.get("snippets", {})
    for i, sid in enumerate(a.shots):
        s = shots[sid]; spec = s.get("alt", {"method": "chars"}); m = spec["method"]
        for k in range(a.start, a.start + a.n):
            name = f"{sid}_e{k}"
            if list(alt.glob(f"{name}_*.png")):
                continue
            sd = str(a.seed_base + i * 100 + k)
            base = [PY, str(GEN), "--width", "1344", "--height", "768", "--seed", sd, "--prefix", f"film/{name}", "--out", str(alt)]
            if m == "photo":
                photo = out / spec.get("photo", f"masters/crop_{sid}.png")
                cmd = base + ["--model", "qwen-edit", "--prompt", fill(spec["prompt"], snip), "--ref", str(photo)]
            elif m == "lora":
                c = chars[spec["char"]]
                p = c.get("lora_prompt", c["look"]) + ". " + fill(spec["prompt"], snip)
                cmd = base + ["--model", "qwen21", "--lora", spec["lora"], "--prompt", p]
            else:   # chars：照 make_film frames() 的組法
                keep = " ".join(f"Keep exactly the same person as <image{j}>: same face, hairstyle and clothes ({chars[c]['look']})."
                                for j, c in enumerate(s["refs"], 1))
                set_s = (" " + cfg["set_sentence"].format(n=len(s["refs"]) + 1)) if s.get("scene") else ""
                p = keep + set_s + " New photo: " + cfg["cine"] + fill(s["frame"], snip) + cfg.get("frame_suffix", "")
                cmd = base + ["--model", "qwen-edit", "--prompt", p]
                for c in s["refs"]:
                    cmd += ["--ref", str(out / "chars" / f"{c}.png")]
                if s.get("scene"):
                    cmd += ["--ref", str(out / "masters" / f"crop_{sid}.png")]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(sid, m, k, "ok" if r.returncode == 0 else "FAIL " + (r.stdout + r.stderr)[-300:], flush=True)


if __name__ == "__main__":
    main()
