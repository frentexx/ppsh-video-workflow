"""首幀局部修圖：qwen-edit「其他都不動、只改這幾處」（2026-10-23《團結》N1 兩段式修圖，採用）。

什麼時候用：
  - 兩人同框、其中一人有角色 LoRA：qwen-edit 掛不上 LoRA（LoRA 是 Qwen-Image 2.1 練的），qwen21＋LoRA 又會外溢成雙胞胎
    → 先用 qwen-edit 生出動作／構圖對的首幀，再用本工具以「LoRA 生的單人近景」當 <image2>，把那人的臉與髮型換過去
  - 背景出現一塊空白牆、材質不對（紅磚、窗台）等局部錯誤
  （另一條路：regional_inpaint.py 分區重繪，兩人分得開時更準）

提示詞寫法（關鍵是先講「保留什麼」，再編號列出「只改哪幾處」）：
  Edit <image1>, keeping everything else exactly the same: the same two boys in the same poses, positions, clothes and framing.
  Make two changes only. 1) The boy on the RIGHT must have exactly the face and the hairstyle of the boy in <image2>: ...
  2) Replace the plain blank wall section in the middle of the background so the wall runs continuously across the whole frame: ...
一次改太多處容易連構圖一起變；改不完就分兩次（《團結》N1：第 1 次換臉＋補窗，第 2 次只把窗下改紅磚）。

用法（H3 venv 的 python，ComfyUI 要開著）：
  edit_fix.py --base 首幀.png [--ref 參考臉.png ...] --prompt "..."（或 --prompt-file 提示詞.txt）--name N1E --out out/fix [--n 4] [--seed 9400]
  → out/fix/<name>_e<k>_00001_.png，已存在的候選會跳過
"""
import argparse
import os
import subprocess
from pathlib import Path

PY = os.environ.get("PY_H3", r"C:\AI\H3\venv\Scripts\python.exe")
GEN = Path(os.environ.get("AI_TOOLS", r"C:\AI\tools")) / "gen_image.py"


def main():
    ap = argparse.ArgumentParser(description="qwen-edit 局部修圖（其他不動）")
    ap.add_argument("--base", required=True, help="要修的圖（<image1>）")
    ap.add_argument("--ref", action="append", default=[], help="參考圖（依序是 <image2>、<image3>），最多 2 張")
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--name", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=4); ap.add_argument("--seed", type=int, default=9400)
    ap.add_argument("--width", default="1344"); ap.add_argument("--height", default="768")
    a = ap.parse_args()
    p = a.prompt or Path(a.prompt_file).read_text(encoding="utf-8").strip()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for k in range(1, a.n + 1):
        name = f"{a.name}_e{k}"
        if list(out.glob(f"{name}_*.png")):
            continue
        cmd = [PY, str(GEN), "--model", "qwen-edit", "--width", a.width, "--height", a.height, "--prompt", p,
               "--seed", str(a.seed + k), "--prefix", f"film/{name}", "--out", str(out), "--ref", a.base]
        for r in a.ref:
            cmd += ["--ref", r]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(name, "ok" if r.returncode == 0 else "FAIL " + (r.stdout + r.stderr)[-300:], flush=True)


if __name__ == "__main__":
    main()
