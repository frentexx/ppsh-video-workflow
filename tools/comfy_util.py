"""本地工具共用的 ComfyUI 小函式（bg_inpaint.py、regional_inpaint.py 用）。
COMFY_HOST、COMFY_DIR 環境變數與 configs/profile.cmd 一致。"""
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
COMFY = Path(os.environ.get("COMFY_DIR", r"C:\AI\H3\ComfyUI-0.36.0"))

# Qwen-Image 2.1（int8 壓縮版）三件組：生圖／重繪都用這組
QWEN21 = {
    "unet": "qwen_image_2.1_int8_convrot.safetensors",
    "clip": "qwen3vl_8b_int8_convrot.safetensors",
    "vae": "qwen_image_2.1_vae_bf16.safetensors",
}


def req(path, data=None):
    r = urllib.request.Request(HOST + path, data=json.dumps(data).encode() if data is not None else None,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read().decode())


def to_input(src, name=None):
    """把檔案複製進 ComfyUI/input，回傳在 ComfyUI 裡的檔名"""
    name = name or Path(src).name
    shutil.copy2(src, COMFY / "input" / name)
    return name


def run_graph(graph, dst, label=""):
    """送出工作流、等待完成、把第一張輸出圖複製到 dst。成功回傳 True。"""
    t0 = time.time()
    pid = req("/prompt", {"prompt": graph})["prompt_id"]
    while True:
        time.sleep(3)
        h = req(f"/history/{pid}")
        if pid in h:
            break
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        m = [x for x in st["messages"] if x[0] == "execution_error"]
        print(label, "ERROR", m[0][1]["exception_message"][:300] if m else st, flush=True)
        return False
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    for o in h[pid]["outputs"].values():
        for f in o.get("images", []):
            shutil.copy2(COMFY / "output" / f.get("subfolder", "") / f["filename"], dst)
            print(label, f"ok {time.time() - t0:.0f}s → {dst}", flush=True)
            return True
    print(label, "沒有輸出圖", flush=True)
    return False
