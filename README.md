# 影音工作流：地端 AI 校園短片製作（屏北高中改作版）

以三師爸（山獅霸的多重宇宙，[mathruffian-dot](https://github.com/mathruffian-dot)）公開的
[shanshiba-workflow-16gvram-32gram](https://github.com/mathruffian-dot/shanshiba-workflow-16gvram-32gram)（16GB 顯卡＋32GB 記憶體版，commit `1b2eecc`）為底，
併入屏北高中製作校園短片《團結》（2026-10-19～23）期間的本地增強、量測工具與實驗結論。

**目的**：開新影片專案時，AI 只要讀 [AGENTS.md](AGENTS.md) 就能直接用最新做法，不必從原版重踩一次坑。

- 流程：Qwen-Image 生定妝照與首幀 → MiniMax H3（Ref2VA）把首幀變成會說話的影片 → BreezyVoice 台灣國語配音 → Music 3 配樂 → 自動剪接與自審。全部本機執行。
- 機器：LIB-office（RTX 5060 Ti 16GB＋32GB RAM、Windows 11）實際跑完一支 2 分 26 秒、38 鏡的片。
- 原版的完整說明保留在 [README_三師爸原版.md](README_三師爸原版.md)，安裝看 [AGENT_SETUP.md](AGENT_SETUP.md)。

> ⚠️ **非商業用途**（校內教學、宣導）。Qwen-Image 2.1、Breeze TTS 2 只能非商用；MiniMax H3 授權排除美國／歐盟／英國／南韓；公開內容須標示 AI 生成。詳見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 從三師爸原版改了哪些

| 檔案 | 改了什麼 | 依據 |
|---|---|---|
| `pipeline/template_local/make_film.py` | H3 預設改 **DMAD 8 步、強度 0.8**（`h3.dmad` 可改）；`h3.setting_by_scene` 依場景分開寫；單鏡 `constraints` 整組取代全片約束；單鏡 `h3_lora` 疊動作 LoRA（自動關 draft、手動疊 DMAD）；`masters` 可直接用**實景照**（`{"photo": …}`）；`snippets` 讓首幀提示詞引用共用描述；配樂段落數依片長計算 | docs/10、docs/09 |
| `tools/h3_shot.py` | `ref_image_size` 可由 spec 設定（原本寫死 `match`） | docs/10 第 1 階段 G 組 |
| `docs/02_端到端流程.md`、`docs/03_規則與踩坑.md` | 加註：DMAD 預設改 8 步；多人走位用側面構圖 | docs/10、docs/09 |
| `pipeline/template_local/README.md` | 加上新欄位說明 | — |
| `README.md` → `README_三師爸原版.md` | 改名保留，DMAD 兩處加註 | — |
| `LICENSE`、`LICENSE-docs.md`、`THIRD_PARTY_NOTICES.md` | 加註改作出處與新增工具的模型授權 | — |
| `.gitignore` | 排除 `input_*/`、`out/`、照片 | 個資 |

## 新增了哪些

| 位置 | 內容 |
|---|---|
| [AGENTS.md](AGENTS.md)、`CLAUDE.md` | 給 AI 的入口：流程、預設值、必讀的坑、量測步驟 |
| [docs/00_新片SOP.md](docs/00_新片SOP.md) | 新片標準流程：劇本 → 分鏡 → 依機位拍實景照 → 首幀 → 量測 → H3 → 量測 → 後製 |
| [docs/08_四道工序與LoRA.md](docs/08_四道工序與LoRA.md) | 四道工序、各種 LoRA 的定位；動作 LoRA、雙角色 LoRA 實測 |
| [docs/09_失敗紀錄.md](docs/09_失敗紀錄.md) | **做新片前必讀**：look 寫下半身會毀掉近景、捲袖變長袖、LoRA 外溢、配樂長度、背景不像實景 |
| [docs/10_影片品質實驗.md](docs/10_影片品質實驗.md) | 13 個影響因素排序與 5 階段對照實驗結果（步數、注意力、取樣器、場景描述、背景重繪） |
| [docs/11_H3社群LoRA.md](docs/11_H3社群LoRA.md) | 西方／中國社群 H3 LoRA 調查與實驗方案 |
| [docs/12_實景拍攝與機位參考照.md](docs/12_實景拍攝與機位參考照.md) | 校園實景拍攝規則、依分鏡拍機位參考照 |
| [templates/新片/](templates/新片/README.md) | 新片 `film.json` 範本（預設值套用實驗結論）、欄位寫法、機位表 |
| `tools/bg_inpaint.py` | 首幀背景對齊實景：人物遮罩保留＋只重畫背景（原 `bg_inpaint.py`） |
| `tools/alt_frames.py` | 首幀另外三種做法：實景照上加人／角色 LoRA 近景／定妝照多候選（原 `gen_v2_frames.py`） |
| `tools/edit_fix.py` | qwen-edit 局部修圖：換臉、補牆（原 `gen_N1_fix.py`、`gen_N1_fix2.py`） |
| `tools/regional_inpaint.py` | 同畫面多角色 LoRA：分區重繪 |
| `tools/remap_voice.py` | 改劇本後配音檔自動改號（原 `remap_voice_v2.py`，改成依鏡號＋台詞比對，不必手填位移量） |
| `tools/h3_ab.py` | H3 設定／動作 LoRA 對照實驗＋自動量臉（合併原 `exp_h3.py`、`lora_ab.py`） |
| `tools/comfy_util.py` | 上面幾支共用的 ComfyUI 呼叫 |
| [tools/measure/](tools/measure/README.md) | 量測工具：`facecheck.py`（逐格換臉檢查）、`bgcheck.py`（背景 vs 實景、鏡頭間一致、影片漂移） |
| `docs/img/四道工序與LoRA.svg` | 流程圖 |

原《團結》腳本裡寫死的路徑、鏡號、角色都改成參數或 film.json 設定；只對《團結》有用的一次性腳本（`patch_*.py`、`gen_teacher6.py` 等）沒有收。

## 目錄

```
AGENTS.md / CLAUDE.md       給 AI 的入口（先讀這個）
README.md                   本檔
README_三師爸原版.md         原版說明（安裝、十條經驗、授權）
AGENT_SETUP.md              安裝手冊（原版）
docs/
  00_新片SOP.md ⭐           新片標準流程
  01～07                     原版文件（02、03 有加註）
  08～12                     本 repo 新增：LoRA、失敗紀錄、品質實驗、社群 LoRA、實景拍攝
  hardware.md               硬體實測（原版）
templates/新片/ ⭐           film.json 範本、欄位說明、機位表
pipeline/template_local/    make_film.py（本 repo 增強版）＋原版範例 film.json
tools/                      全域工具（裝到 C:\AI\tools）；本 repo 新增 7 支＋measure/
setup/ sfx/ agent/ configs/ 原版
```

## 快速開始（已裝好環境的 LIB-office）

1. `tools/*.py` 複製到 `C:\AI\tools\`（覆蓋 `h3_shot.py`）；`tools/measure/*.py` 複製到 `D:\AI\facecheck\`。
2. 照 [templates/新片/README.md](templates/新片/README.md) 建 `D:\AI\films\<片名>\`。
3. 照 [docs/00_新片SOP.md](docs/00_新片SOP.md) 一步一步做。

全新電腦從零安裝：看 [AGENT_SETUP.md](AGENT_SETUP.md)（原版，模型約 150GB）。

## 授權

| 內容 | 授權 |
|---|---|
| 程式（`*.py`、`*.ps1`、`*.cmd`、設定檔） | MIT，見 [LICENSE](LICENSE)；原作 © 山獅霸的多重宇宙（mathruffian-dot），修改與新增 © 屏北高中 fuwen |
| 文件與素材（`*.md`、圖片） | CC BY-NC 4.0，見 [LICENSE-docs.md](LICENSE-docs.md)；轉用請標示原作者與改作者、不可商用 |
| 第三方模型 | 各自授權，見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

**本 repo 不含**：模型權重、學生照片、本人照片與聲音、任何 `input_*` 資料夾、成片。
