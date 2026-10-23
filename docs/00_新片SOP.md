# 00 新片 SOP（本 repo 的標準做法）

> 依《團結》（2026-10-19～23）實際走過的流程與實驗結論整理。原版各步驟的細節仍在 `02_端到端流程.md`，本 SOP 只寫**順序、預設值與關卡**。
> 機器：LIB-office（RTX 5060 Ti 16GB＋32GB RAM）。影片一律在 `D:\AI\films\<片名>\` 跑。

```
劇本 ─✅→ 分鏡（鏡表）─✅→ 依機位拍實景照 → 角色定妝照／LoRA ─✅→ 首幀 → 【量測①】─✅→ 配音 ─✅→ H3 → 【量測②】─✅→ 後製 → 自審 ─✅→ 上片
                                                                                ✅ = 人工關卡
```

| # | 步驟 | 工具 | 產出 | 關卡／量測 |
|---|---|---|---|---|
| 1 | 劇本 | 人＋AI（`agent/skills/shanshiba-drama`） | `劇本.md` | ✅ 使用者確認 |
| 2 | 分鏡 | 依 `templates/新片/README.md` 的分鏡規則寫進 `film.json` 的 `shots` | `film.json`、`鏡表.md` | ✅ 確認景別、構圖 |
| 3 | 機位與實景照 | `templates/新片/機位表.md`、`docs/12` | `input_scene/*.jpg` | 使用者拍；不能有人、不能有字 |
| 4 | 場景母版 | `make_film.py masters`（`masters` 寫 `{"photo": …}`） | `out/masters/` | 看裁切 |
| 5 | 角色 | `make_film.py chars`；常出場的角色訓練 LoRA（`setup/lora/`、`docs/08`） | `out/chars/`、LoRA | ✅ 定妝照定案後**不再換** |
| 6 | 首幀 | `make_film.py frames`；不適合的鏡用 `tools/alt_frames.py`、局部修 `tools/edit_fix.py`、雙 LoRA `tools/regional_inpaint.py` | `out/first/` | **先看前 2～3 張再整批** |
| 7 | 量測① | `bgcheck.py ref`（背景 vs 實景，目標 ≥ 0.75）、`bgcheck.py matrix`（同場景一致） | 分數＋熱度圖 | ✅ 看 `out/first/_sheet.jpg`，建 `frames_ok` |
| 8 | 配音 | `make_film.py voices`（改劇本後先 `tools/remap_voice.py`） | `out/voice/` | ✅ 試聽 |
| 9 | H3 | `make_film.py h3`（預設 DMAD 8 步／0.8） | `out/h3/<鏡>/clip.mp4` | — |
| 10 | 量測② | 每鏡 `facecheck.py`（換臉）、`bgcheck.py video`（偷換場景、推近） | 曲線圖 | 不合格：換 seed、改首幀，或剪掉漂移的後段 |
| 11 | 後製 | `make_film.py amb edl music ending cut` | 成片 | 片超過 2 分鐘：配樂分段生 |
| 12 | 自審 | `make_film.py review` | 自動檢查報告 | ✅ **人一定要看成片**（嘴型、配音腔調機器量不到） |

## 每一步的重點（踩過的坑）

### 1～2 劇本與分鏡
- 對白鏡＝單人近景（臉佔畫高 10% 以上）；遠景臉會崩，放大救不回。
- 多人走位用**側面構圖**；縱深構圖 H3 會演成並肩走。
- 避免手拿會掉落的道具；台語詞、罕用字換說法（配音會念錯）。
- 老師與學生之間不得有肢體碰觸；學生之間的衝突可以拍（要力道時 `h3_lora` Combat 0.5～0.7）。

### 3～4 實景照與場景母版
- **一開始就用實景照**，不要先畫 AI 場景再補救（`docs/12`）。
- 每個機位照分鏡拍，**坐著的人物近景用坐姿高度拍**；只用一張站姿斜拍照，背景透視會錯。
- 反覆出現的場景（走廊方向、牆面材質）寫進 `snippets`，各鏡引用。
- `scene` 裁切框在正規化座標下要**正方形**；框只管背景範圍，不控制景別。

### 5 角色
- `look` 只寫到上衣；完整版放 `look_full`（寫了長褲鞋子會被拉成全身鏡，`docs/09`）。
- 制服明寫 `SHORT-sleeve … bare forearms, never long sleeves`；不要寫「捲袖」。
- LoRA 訓練：資料夾不能有子資料夾、每 400 步存檔、每批樣圖跟本人照片比對（可用 facecheck 算相似度），變差就停。只有正面像訓練的 LoRA 側臉會跑掉。
- `make_lora_dataset.py` 會補生缺號的圖：剔除壞圖後重跑，會用同 seed 生出一樣的壞圖。

### 6 首幀
- 景別寫在 `frame` 句首並寫明到身體哪裡；共用光線寫 `cine`（陰天柔光），不要 green／teal。
- 遠景多人鏡：`alt_frames.py` photo 方法（實景照上加人）。
- 有角色 LoRA 的單人近景：`alt_frames.py` lora 方法（qwen21＋LoRA、**不給場景參考圖**）。
- 兩人同框其中一人有 LoRA：photo 做構圖 → `edit_fix.py` 換臉，或 `regional_inpaint.py` 分區重繪（兩人分得開時）。qwen-edit 掛不上 LoRA。
- 背景不像實景：`bg_inpaint.py`（人物不動、只重畫背景）。qwen-edit 直接換背景會改構圖、換臉。

### 9 H3
- 預設 DMAD 8 步／強度 0.8、euler、INT8 注意力（PyTorch 注意力慢 58～75% 沒更好；lcm 無明確改善；`ref_image_size=max` 只給首幀時無作用；另附身份參考圖反而更不穩）。
- **H3 背景完全由首幀決定**，改場景描述改不動；要修背景就修首幀。
- 動作 LoRA 只加力道，救不了「演錯」的鏡頭；演錯要改首幀構圖與提示詞。
- 不確定設定時用 `tools/h3_ab.py` 做對照（同首幀、同 seed、同音軌，一次改一個因素）。
- 跑長批次前確認分頁檔在 D 槽（虛擬記憶體不足會讓長鏡失敗）。

### 10 量測②
- facecheck：SFace cosine ≥ 0.363 視為同一人；曲線明顯下降＝換臉。側臉、低頭本來就會降，要看圖判斷。
- 換臉只發生在後段時，可以把 `cut_out` 剪在換臉之前（《團結》N1 剪在 3.0 秒）。

### 11 後製
- Music 3 單次實務上約 2 分鐘就是上限；段落多時人聲殘留可能暴增。超過 2 分鐘的片分兩段配樂再交叉淡入，或沿用定案配樂用 ffmpeg 延長。
- `review` 自動檢查：響度約 −15.5 LUFS、無黑畫面／凍結／台詞重疊。

## 檔案放哪裡

| 內容 | 位置 | 進 git？ |
|---|---|---|
| 劇本、film.json、鏡表、機位表 | 影片資料夾（Google Drive 的專案資料夾留一份） | ✅（各片自己的專案 repo） |
| `out/`（首幀、影片、配音） | `D:\AI\films\<片名>\out\` | ❌ |
| `input_scene/`、`input_person/`、`input_voice/`、`input_pic/` | 影片資料夾 | ❌ 一律不進 git、不送雲端 |
| 成片 | 專案資料夾 `成片/` | ❌（太大） |
