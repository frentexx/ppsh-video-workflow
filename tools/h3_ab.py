"""H3 設定／動作 LoRA 對照實驗（合併《團結》的 exp_h3.py 與 lora_ab.py，2026-10-22～23）。

原則：同首幀、同 seed、同音軌、同提示詞，一次只改一個因素；結果自動跑 facecheck 量換臉。
底稿＝make_film.py 產生的 out/h3/<鏡>/spec.json（＝A 組「現行」，影片直接沿用不重跑）。

內建變體（名稱: spec 覆寫；dmad=None＝不掛加速 LoRA）：
  B_DMAD4_1.0   原版預設（4 步 1.0）       C_DMAD8_0.8   本 repo 預設（8 步 0.8）   D_DMAD6_0.8
  E_無加速20步  res_multistep 20 步        F_PyTorch注意力                           G_lcm取樣
  H_ref_max     ref_image_size=max（只給首幀時無作用，留作對照）
  CB05／CB06／CB07／CB10   疊 H3_Combat_V2（動作力道）    MR05／MR09   疊 Motion_Repair_V2
自訂變體：--variants 我的.json（同樣格式的 {名稱: 覆寫}；覆寫可含 "extra_lora": [{"name":…, "strength":…}]、"first_frame"）。

《團結》結論（詳見 docs/10_影片品質實驗.md）：C 8 步 0.8 ＝ 20 步的臉部穩定度、時間約一半；PyTorch 注意力慢 58～75% 沒更好；
lcm 有升有降；ref_max 與 C 逐位元組相同；Combat 0.5～0.7 有力道、1.0 會升級成扭打；Motion_Repair 救不了走位錯的鏡頭。

用法（H3 venv 的 python，ComfyUI 要開著）：
  h3_ab.py <變體,...> <鏡,...> [--dir 影片資料夾] [--base 變體] [--variants 自訂.json] [--first 另一張首幀.png]
  例：h3_ab.py B_DMAD4_1.0,E_無加速20步 N1,S22      h3_ab.py CB06,CB07 N1 --base C_DMAD8_0.8
  → out/ab/<鏡>/<變體>/clip.mp4、time.txt；out/ab/<鏡>/_face/（facecheck 曲線）、_<變體>.jpg（縮圖）
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

PY = os.environ.get("PY_H3", r"C:\AI\H3\venv\Scripts\python.exe")
H3SHOT = Path(os.environ.get("AI_TOOLS", r"C:\AI\tools")) / "h3_shot.py"
FACEPY = os.environ.get("PY_FACECHECK", r"D:\AI\facecheck\venv\Scripts\python.exe")
FACECHECK = os.environ.get("FACECHECK", r"D:\AI\facecheck\facecheck.py")
DMAD = "dmad_h3_4step_lora_critic_comfy.safetensors"
CB, MR = "H3_Combat_V2.safetensors", "Motion_Repair_V2.safetensors"


def dmad(steps, st):
    return dict(draft=False, steps=steps, sampler="euler", shift={"video": 12, "audio": 2}, dmad=st)


VARIANTS = {
    "B_DMAD4_1.0": dmad(4, 1.0),
    "C_DMAD8_0.8": dmad(8, 0.8),
    "D_DMAD6_0.8": dmad(6, 0.8),
    "E_無加速20步": dict(draft=False, steps=20, sampler="res_multistep", shift={"video": 12, "audio": 3}, dmad=None),
    "F_PyTorch注意力": dict(attention="pytorch attention"),
    "G_lcm取樣": dict(sampler="lcm"),
    "H_ref_max": dict(ref_image_size="max"),
    **{f"CB{round(s * 10):02d}": dict(extra_lora=[{"name": CB, "strength": s}]) for s in (0.5, 0.6, 0.7, 1.0)},
    **{f"MR{round(s * 10):02d}": dict(extra_lora=[{"name": MR, "strength": s}]) for s in (0.5, 0.9)},
}


def build(base_spec, overs):
    spec = json.loads(json.dumps(base_spec))
    lora = spec.get("lora") or []
    dm = next((l for l in lora if DMAD in l["name"]), None)
    extra = [l for l in lora if DMAD not in l["name"]]                  # 現行的動作 LoRA 保留
    for o in overs:
        o = dict(o)
        if "dmad" in o:
            st = o.pop("dmad"); dm = {"name": DMAD, "strength": st} if st else None
        if "extra_lora" in o:
            extra = extra + o.pop("extra_lora")
        spec.update(o)
    if spec.get("draft") is not False:                                 # 底稿是 draft=true（DMAD 4 步）：draft 會把自訂 LoRA 蓋掉 → 改手動疊
        spec.update(draft=False, steps=4, sampler=spec.get("sampler", "euler"), shift=spec.get("shift", {"video": 12, "audio": 2}))
        dm = dm or {"name": DMAD, "strength": 1.0}
    spec["lora"] = ([dm] if dm else []) + extra
    if not spec["lora"]:
        spec.pop("lora")
    return spec


def main():
    ap = argparse.ArgumentParser(description="H3 對照實驗：一次只改一個因素")
    ap.add_argument("variants"); ap.add_argument("shots"); ap.add_argument("--dir", default=".")
    ap.add_argument("--base"); ap.add_argument("--variants-file", "--variants", dest="vfile"); ap.add_argument("--first")
    a = ap.parse_args()
    here = Path(a.dir).resolve(); allv = dict(VARIANTS)
    if a.vfile:
        allv.update(json.loads(Path(a.vfile).read_text(encoding="utf-8")))
    base_over = [allv[a.base]] if a.base else []
    for shot in a.shots.split(","):
        src = here / "out" / "h3" / shot; sd = here / "out" / "ab" / shot; sd.mkdir(parents=True, exist_ok=True)
        base_spec = json.loads((src / "spec.json").read_text(encoding="utf-8"))
        first = a.first or base_spec["first_frame"]
        A = sd / "A_現行"; A.mkdir(exist_ok=True)
        if not (A / "clip.mp4").exists() and (src / "clip.mp4").exists() and not a.first:
            shutil.copy2(src / "clip.mp4", A / "clip.mp4")
        for n in a.variants.split(","):
            tag = f"{a.base}+{n}" if a.base else n; od = sd / tag
            if (od / "clip.mp4").exists():
                continue
            od.mkdir(exist_ok=True)
            spec = build(base_spec, base_over + [allv[n]]); spec["first_frame"] = str(first)
            if Path(spec.get("audio", {}).get("fixed", {}).get("file", "")).name == "guide.wav":   # 音軌固定用原鏡的 guide.wav
                spec["audio"]["fixed"]["file"] = str(src / "guide.wav")
            (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
            t0 = time.time()
            r = subprocess.run([PY, str(H3SHOT), str(od / "spec.json"), "--out", str(od)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            sec = round(time.time() - t0); ok = r.returncode == 0 and (od / "clip.mp4").exists()
            (od / "time.txt").write_text(str(sec), encoding="utf-8")
            print(shot, tag, "ok" if ok else "FAIL " + (r.stdout + r.stderr)[-600:], f"{sec}s", flush=True)
            if ok:   # 縮圖：每秒 1.5 張排成 4×3，方便並排看動作
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(od / "clip.mp4"), "-vf", "fps=1.5,scale=448:-1,tile=4x3",
                                "-frames:v", "1", str(sd / f"_{tag}.jpg")])
        clips = sorted(str(p) for p in sd.glob("*/clip.mp4"))
        if Path(FACECHECK).exists() and clips:
            subprocess.run([FACEPY, "-X", "utf8", FACECHECK, str(first), *clips, "--out", str(sd / "_face")])
        else:
            print("（找不到 facecheck，略過臉部量測；設定環境變數 FACECHECK／PY_FACECHECK）")


if __name__ == "__main__":
    main()
