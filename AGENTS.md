# 影音工作流（給 AI 的入口）

> 地端 AI 校園短片工作流。改作自三師爸 `mathruffian-dot/shanshiba-workflow-16gvram-32gram`（`1b2eecc`），併入屏北高中《團結》（2026-10-19～23）的增強與實驗結論。
> 建立：2026-10-23。**開新影片專案時先讀這份，再讀 `docs/00_新片SOP.md` 與 `docs/09_失敗紀錄.md`。**
> 所有給使用者看的文字、程式註解、文件一律繁體中文（台灣用語）。

## 這個 repo 是什麼、不是什麼

- **是**：工作流的程式、範本、規則與實驗結論（唯一真相來源）。新片的劇本、film.json 放在各片自己的專案資料夾，影片在 `D:\AI\films\<片名>\` 跑。
- **不是**：某一支片的製作資料夾。不要在這裡放 `out/`、照片、聲音。
- 原版文件 `docs/01`～`07`、`README_三師爸原版.md`、`AGENT_SETUP.md` 仍有效；**與本檔衝突時以本檔和 `docs/00`、`08`～`12` 為準**（最常見的是 DMAD 步數）。

## 流程（細節見 `docs/00_新片SOP.md`）

```
劇本 ─✅→ 分鏡 ─✅→ 依機位拍實景照 → 角色定妝照／LoRA ─✅→ 首幀 → 量測① ─✅→ 配音 ─✅→ H3 → 量測② ─✅→ 後製 → 自審 ─✅→ 上片
```

| 步驟 | 指令（在 `D:\AI\films\<片名>\`，H3 venv：`C:\AI\H3\venv\Scripts\python.exe`） |
|---|---|
| 建片 | 複製 `templates/新片/*` 與 `pipeline/template_local/make_film.py` |
| 母版／定妝照／首幀 | `make_film.py masters chars frames` |
| 首幀另做 | `tools/alt_frames.py`、`edit_fix.py`、`regional_inpaint.py`、`bg_inpaint.py` |
| 量測① | `bgcheck.py ref …`、`bgcheck.py matrix …`（facecheck venv） |
| 配音 | `make_film.py voices`（改過劇本先跑 `tools/remap_voice.py --dry` 再正式跑） |
| H3 | `make_film.py h3`（`ONLY="S02 S05"` 只跑指定鏡） |
| 量測② | `facecheck.py out/first/<鏡>.png out/h3/<鏡>/clip.mp4 --out …`、`bgcheck.py video …` |
| 後製＋自審 | `make_film.py amb edl music ending cut review` |
| 設定對照 | `tools/h3_ab.py <變體,...> <鏡,...>` |

## 預設值（已實測，不要改回原版）

| 項目 | 預設 | 原版 | 依據 |
|---|---|---|---|
| H3 加速 | DMAD **8 步、強度 0.8**、euler、shift 12／2 | DMAD 4 步 1.0（`draft: true`） | 4 步動作大會換臉（N1 臉部最低 0.27）；8 步 0.61、等同 20 步、時間約一半 |
| 注意力 | comfy kitchen INT8 | 同 | PyTorch 注意力慢 58～75%、沒更好 |
| `ref_image_size` | match | 同 | 只給首幀時 max 無作用（影片逐位元組相同） |
| 身份參考圖 | 不附 | 不附 | 附了反而更不穩（最低 0.68→0.11） |
| 場景母版 | **實景照**（`masters` 寫 `{"photo": …}`） | AI 生成 | H3 背景完全由首幀決定，AI 場景不像本校 |
| H3 場景描述 | `h3.setting_by_scene` 依場景分開寫 | 全片一句 | 無害、提示詞乾淨（但改不動背景） |
| 首幀光線 | `cine` 寫陰天柔光；不寫 green／teal | 早晨斜陽 | 正午硬光不像實景；調色詞讓整片發綠 |
| 制服 | `SHORT-sleeve … bare forearms, never long sleeves` | — | 寫「捲袖」會變長袖 |
| 動作 LoRA | 不掛；學生推擠要力道才掛 Combat 0.5～0.7 | — | 1.0 會升級成扭打、壓過約束 |

## 必讀的坑（每一條都重跑過好幾小時）

1. **`look` 只寫到上衣**：寫了長褲／裙子／鞋子，定妝照與首幀都會被拉成全身鏡，臉只剩十幾像素，後面全毀。完整版放 `look_full`；會看到腿的鏡把下半身寫進那一鏡的 `frame`。
2. **景別寫在 `frame` 句首**，並寫到身體哪裡；裁切框（`scene`）只管背景範圍、不控制景別，且正規化座標要正方形。
3. **整批跑之前先看前 2～3 張**；「有時候會對」等於沒修好；修就要修在 film.json，不要只改獨立腳本。
4. **H3 背景完全由首幀決定**：背景錯了只能修首幀（`bg_inpaint.py`），改 H3 提示詞沒用。
5. **多人走位用側面構圖**；縱深構圖 H3 會演成並肩走。動作 LoRA 救不了演錯的鏡頭。
6. **qwen-edit 掛不上角色 LoRA**；qwen21＋LoRA 兩人同框會外溢成雙胞胎 → 先做構圖，再 `edit_fix.py` 換臉或 `regional_inpaint.py` 分區重繪。hook 區域 LoRA 不支援 int8 模型。
7. **qwen-edit 直接換背景會改構圖、換臉** → 用 `bg_inpaint.py`（人物像素貼回）。實景照裡的班級牌會被畫出來，負面詞加 sign／plaque。
8. **老師 LoRA 只有正面像時，側臉會跑掉** → 老師鏡頭盡量正面。
9. **避免手拿會掉落的道具**；快速動作中物品會糊成色塊、前後不一致。
10. **配樂單次約 2 分鐘就是上限** → 長片分段生再交叉淡入。
11. **台語詞（歹勢）與罕用字（跩）配音會念錯** → 換說法或加注音。
12. **edge-tts 要 7.3.1 以上**，且 `C:\AI\Voice\venv\Scripts` 要在 PATH；找不到時 make_film 會默默改用 Breeze 做答案卷，挑音變不準。
13. **影片在 D 槽跑**：LIB-office 的 C 槽只剩約 8GB，`out/` 放 Google Drive 底下會塞爆 Drive 快取；分頁檔要在 D 槽，否則長鏡、LoRA 訓練會「虛擬記憶體不足」。
14. **改劇本插入台詞後配音會錯位** → `tools/remap_voice.py`。
15. LoRA 訓練：資料夾不能有子資料夾；`make_lora_dataset.py` 會用同 seed 補生被剔除的壞圖；每 400 步存檔、樣圖變差就停（《團結》老師 LoRA 用第 400 步，800 步過擬合）。

## 量測步驟（每支新片都要跑）

| 時機 | 指令 | 及格線 |
|---|---|---|
| 首幀後 | `bgcheck.py ref --images "out/first/*.png" --refs <實景照…> --out out/measure/bg_ref` | 背景 vs 實景 ≥ 0.75（AI 場景約 0.66） |
| 首幀後 | `bgcheck.py matrix --images <同場景各鏡> --out out/measure/bg_matrix` | 熱度圖裡明顯偏低的那鏡要重做 |
| H3 後 | `facecheck.py out/first/<鏡>.png out/h3/<鏡>/clip.mp4 --out out/measure/face_<鏡>` | 曲線不掉到 0.363 以下（側臉、低頭會降，看圖判斷） |
| H3 後 | `bgcheck.py video --videos out/h3/*/clip.mp4 --out out/measure/bg_video` | 抓偷換場景、鏡頭推近 |

工具只負責抓錯；**成片一定要人看**（嘴型、腔調、細部材質機器量不到）。安裝見 `tools/measure/README.md`。

## 環境（LIB-office）

- 五個獨立環境：H3（cu130）、Voice（cu130）、BreezeTTS（cu128）、BreezyVoice（cu128／Py3.10）、AI Toolkit（cu130）；量測另有 `D:\AI\facecheck\venv`（CPU）。torch 版本刻意不同。
- `C:\AI` 是 junction 到 `D:\AI`；ComfyUI 在 `C:\AI\H3\ComfyUI-0.36.0`（環境變數 `COMFY_DIR`）。
- 這台沒有 `py -3.12`：建 venv 用 `uv venv --python 3.12`。`UV_CACHE_DIR=D:\uv-cache`。
- ppsh-VR-1 是共用機器（RAM 15.9GB），只適合語音與生圖；排工作前先問使用者，不要跑 H3、不要動它的 ComfyUI（8188）。

## 規則（校內影片）

- 學生照片、本人照片、聲音檔、`input_*` 資料夾**一律不進 git、不送雲端模型**。真實學生照片只取制服款式。
- 老師與學生之間不得有肢體碰觸或衝突；學生之間的衝突可以拍。原住民、新住民身分不當笑點、不疊加弱勢標籤；涉及原住民內容請原住民教師把關。
- 公開影片標示 AI 生成；非商業用途（見 `THIRD_PARTY_NOTICES.md`）。YouTube 上傳前一定先問使用者。
- 實驗結果（對照、失敗原因）要寫回本 repo 對應的 docs（`08`～`12`），並更新本檔的預設值或坑。

## 對照表

| 內容 | 位置 |
|---|---|
| 新片流程 | `docs/00_新片SOP.md` |
| film.json 範本與欄位寫法 | `templates/新片/` |
| 失敗紀錄 | `docs/09_失敗紀錄.md` |
| 品質實驗數據 | `docs/10_影片品質實驗.md` |
| LoRA 定位與實測 | `docs/08_四道工序與LoRA.md`、`docs/11_H3社群LoRA.md` |
| 實景拍攝 | `docs/12_實景拍攝與機位參考照.md` |
| 原版安裝 | `AGENT_SETUP.md`、`docs/06_安裝.md`、`docs/hardware.md` |
| 原始 repo | https://github.com/mathruffian-dot/shanshiba-workflow-16gvram-32gram |
| 製作紀錄（《團結》、SEL） | `G:\我的雲端硬碟\07專案開發\影音生成\`（AGENTS.md、handoff.md） |
