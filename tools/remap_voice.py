"""改劇本（插入／刪除／改台詞）後，讓已挑好的配音檔跟著改號（2026-10-22《團結》第 2 版，泛化）。

為什麼：make_film.py 的配音檔依「台詞在全片的順序」編號（out/voice/bv/line{i}.wav、tw_{i}.wav、cand/line{i}_s*.wav），
前面插一句，後面全部錯位 → 直接跑 voices 會把舊檔配到錯的鏡頭，或整批重生、白挑一次音。
做法：用舊的 out/voice_picks.json（每句記著 shot＋text）比對新的 film.json，
  - 鏡號與台詞都沒變 → 檔案改成新編號（沿用已挑好的音）
  - 新句子或台詞改了 → 刪掉該號的檔與快取，讓 make_film.py voices 重生
執行前會整個備份 out/voice → out/voice_backup_<時間>、voice_picks.json → voice_picks_backup_<時間>.json。

用法：remap_voice.py [--dir 影片資料夾] [--dry]    （--dry 只列出會怎麼改，不動檔案）
之後跑：make_film.py voices（只會生缺的句子）→ 試聽新句子。
"""
import argparse
import json
import re
import shutil
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="台詞順序變動後，配音檔改號")
    ap.add_argument("--dir", default="."); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    here = Path(a.dir).resolve(); out = here / "out"; V = out / "voice"; BV = V / "bv"
    cfg = json.loads((here / "film.json").read_text(encoding="utf-8"))
    new = [(s["id"], s["line"]["text"]) for s in cfg["shots"] if s.get("line")]
    old = json.loads((out / "voice_picks.json").read_text(encoding="utf-8"))

    # 1) 新編號 j ← 舊編號 i（鏡號＋台詞完全相同才沿用）
    used, mp = set(), {}
    for j, (sid, text) in enumerate(new):
        i = next((int(k) for k, v in old.items() if int(k) not in used and v["shot"] == sid and v["text"] == text), None)
        if i is not None:
            used.add(i); mp[i] = j
    regen = [(j, sid, text) for j, (sid, text) in enumerate(new) if j not in mp.values()]
    print("沿用（舊號→新號）：", {i: j for i, j in sorted(mp.items()) if i != j} or "全部不變")
    print("要重生：", *[f"\n  line{j} {sid}「{t}」" for j, sid, t in regen] or ["無"])
    if a.dry:
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    shutil.copytree(V, out / f"voice_backup_{stamp}")
    shutil.copy(out / "voice_picks.json", out / f"voice_picks_backup_{stamp}.json")

    def files(i):
        return [BV / f"line{i}.wav", V / f"tw_{i}.wav", V / f"tw_{i}.mp3", *BV.glob(f"cand/line{i}_s*.wav")]

    # 2) 兩段式改名（先改成暫名、再改成新號），避免號碼互換時互相覆蓋；沒沿用的舊檔直接刪
    for i in {int(k) for k in old} | {int(f.stem[4:].split("_")[0]) for f in BV.glob("line*.wav")}:
        for f in files(i):
            if f.exists():
                if i in mp:
                    f.rename(f.with_name("__tmp_" + f.name))
                else:
                    f.unlink()
    rx = re.compile(r"(?<![0-9A-Za-z_])(line|tw_)(\d+)")
    for f in list(V.rglob("__tmp_*")):
        n = f.name[len("__tmp_"):]
        f.rename(f.with_name(rx.sub(lambda m: m.group(1) + str(mp[int(m.group(2))]), n, count=1)))

    # 3) breezyvoice_pick 的快取 bv/picks.json：改鍵與裡面的候選檔名；沒沿用的刪掉
    pj = BV / "picks.json"
    if pj.exists():
        bp = json.loads(pj.read_text(encoding="utf-8")); nbp = {}
        for k, v in bp.items():
            i = int(k[4:])
            if i in mp:
                s = re.sub(r"(?<![0-9A-Za-z_])line(\d+)_s", lambda m: f"line{mp.get(int(m.group(1)), int(m.group(1)))}_s", json.dumps(v, ensure_ascii=False))
                nbp[f"line{mp[i]}"] = json.loads(s)
        pj.write_text(json.dumps(nbp, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) voice_picks.json：沿用的句子改鍵與路徑；要重生的由 voices 重寫
    vp = {str(j): {**old[str(i)], "file": str(BV / f"line{j}.wav")} for i, j in mp.items()}
    (out / "voice_picks.json").write_text(json.dumps(dict(sorted(vp.items(), key=lambda t: int(t[0]))), ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(f"完成；備份在 out/voice_backup_{stamp}。下一步：make_film.py voices")


if __name__ == "__main__":
    main()
