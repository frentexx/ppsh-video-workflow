# 新片範本

開新片時複製這個資料夾，流程照 [docs/00_新片SOP.md](../../docs/00_新片SOP.md)。

```powershell
# 例：片名資料夾叫 newfilm（影片一律在 D 槽跑，不要在 Google Drive 底下跑——out/ 會塞爆 C 槽的 Drive 快取）
$R = "G:\我的雲端硬碟\07專案開發\影音工作流"
New-Item -ItemType Directory D:\AI\films\newfilm
Copy-Item "$R\templates\新片\*" D:\AI\films\newfilm\
Copy-Item "$R\pipeline\template_local\make_film.py" D:\AI\films\newfilm\
```

| 檔案 | 用途 |
|---|---|
| `film.json` | 整支片的設定，make_film.py 只讀這個檔 |
| `機位表.md` | 分鏡定稿後，每個機位要拍的實景照（位置、高度、角度、景別、時段） |

## film.json 欄位（只列跟原版不同或最容易寫錯的）

完整欄位見 `pipeline/template_local/README.md`；以下是本 repo 的增強與《團結》學到的寫法。

| 欄位 | 寫法 | 為什麼 |
|---|---|---|
| `repo_dir` | 本 repo 的**絕對路徑** | 片放在 D 槽，相對路徑找不到片尾模板 |
| `cine` | 共用光線寫這裡（預設陰天柔光）；**不要** green／teal 調色詞 | 它接在每張首幀提示詞最前面，定調整片；《團結》寫 cool-green 整片又暗又發綠 |
| `frame_suffix` | 保留「景別照寫、不放寬」「人數照寫」「短袖露前臂」「不要任何字」 | 都是退件過的項目 |
| `snippets` | 反覆出現的場景描述（走廊方向、教室樣貌）寫一次，`frame` 裡用 `{名稱}` 引用 | 《團結》各鏡複製貼上，改一處漏一處，走廊方向前後不一致 |
| `h3.dmad` | 預設 `{"steps": 8, "strength": 0.8}` | 4 步動作大會換臉（docs/10） |
| `h3.setting_by_scene` | 依 `masters` 的鍵分開寫；教室鏡不要提走廊 | 無害、提示詞乾淨；但**改不動背景**，背景由首幀決定 |
| `h3.constraints` | 全片共用；單鏡寫 `constraints` 會**整組取代**、寫 `extra_constraints` 是**追加** | 衝突鏡頭要拿掉「Nobody touches…」那條，只能整組換 |
| `chars.*.look` | 寫到**上衣為止**；制服明寫 `SHORT-sleeve … bare forearms, never long sleeves` | 寫了長褲鞋子就會被拉成全身鏡；寫「捲袖」會變長袖（docs/09） |
| `chars.*.look_full` | 含下半身與鞋子的完整版 | 只給 LoRA 訓練與全身鏡參考，make_film 不讀 |
| `chars.*.lora_prompt` | 有角色 LoRA 時：觸發詞＋外觀 | `tools/alt_frames.py` 的 lora 方法用 |
| `masters.<鍵>` | `{"photo": "input_scene/xxx.jpg"}`＝實景照當母版；字串＝AI 生成 | 實景一開始就用，事後補救很貴（docs/12） |
| `shots[].scene` | `[母版鍵, [x0, y0, x1, y1]]`，**正規化座標要正方形**（寬＝高） | 母版與成品都是 1.75:1，框不是正方形會有空白死區；框大小只管背景範圍，**不控制景別** |
| `shots[].frame` | **景別寫在句首**並寫明到身體哪裡；會看到腿的鏡才寫下半身 | 景別擠到句中就沒份量 |
| `shots[].alt` | 首幀改用 `tools/alt_frames.py`（photo／lora／chars） | 多人走位、有角色 LoRA 時 |
| `shots[].h3_lora` | 例 `[{"name": "H3_Combat_V2.safetensors", "strength": 0.6}]` | 學生推擠要力道時；0.5～0.7，1.0 會升級成扭打；老師在場一律不掛 |
| `shots[].bg_mask`／`bg_scene` | 給 `tools/bg_inpaint.py` 用 | 只有事後補救背景時 |

## 寫分鏡時的規則（《團結》學到的）

- 對白鏡＝**單人近景**（臉大，嘴型才清楚）；遠景臉會崩。
- 多人走位鏡用**側面構圖**（縱深構圖 H3 會演成並肩走）。
- 兩人同框而其中一人有角色 LoRA：不要 qwen21＋LoRA 直接生（外溢成雙胞胎）→ photo 方法做構圖，再 `edit_fix.py` 換臉或 `regional_inpaint.py` 分區重繪。
- 避免手拿會掉落的道具；台語詞（歹勢）與罕用字（跩）配音會念錯，換說法。
- 學生之間的肢體衝突可以拍；**老師與學生之間一律不得有肢體碰觸**。
