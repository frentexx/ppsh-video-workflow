# 11 H3 社群 LoRA 評估與實驗方案

> 📌 本文整理自屏北高中「影音生成」專案製作《團結》（2026-10-19～23）的實驗紀錄，數據與出處照原樣保留。文中「本片」指《團結》或 SEL 第 1 集；角色名（大頭、阿凱、阿文老師、老蔡）是那兩部片的角色。原紀錄提到的比較圖、影片在影音生成專案的 `製作/短片_團結/v2試拍/`，沒有收進本 repo。

> 建立：2026-10-23｜依據：Gemini 建議稿＋兩位研究員調查（西方：Civitai／HuggingFace／ComfyUI 文件；中國：RunningHub／ModelScope／comfyui-wiki／bbs.monster）＋本專案已做的三組實驗（見 `08_四道工序與LoRA.md`）
> 查證限制：Reddit、LiblibAI、吐司、小紅書、知乎都抓不到原文，社群心得多為二手資料；Civitai 下載數為 2026-10-23 當下數字。

## 一、先釐清：LoRA 掛在哪一道工序

| 工序 | 模型 | 能掛的 LoRA | 本專案現況 |
|---|---|---|---|
| 2 生首幀 | Qwen-Image 2.1／Qwen-Image-Edit | **角色 LoRA**（大頭、老師、老蔡） | 已用；qwen-edit 掛不上 |
| 3 生影片 | MiniMax H3（**Ref2VA 模式**：首幀＋固定音軌） | 加速、畫質、動作、運鏡 LoRA | 已用 DMAD 4 步、Combat、Motion_Repair |

**Gemini 稿最大的錯**：把角色 LoRA 列進 H3 的堆疊。我們的角色 LoRA 是 Qwen-Image 練的，H3 讀不了。

## 二、Gemini 建議逐項查證

| Gemini 建議 | 查證結果 | 評估 |
|---|---|---|
| TaoMate 3 步加速 | 存在（阿里 TaoLive） | ❌ 原版要 Hopper 顯卡；屬 FL2VA 系，非 Ref2VA |
| Larry Turbo | 存在（Apache-2.0，HF 約 20 萬次／月） | △ 只寫 t2v／i2v，4 步大動作會拖影；當對照組 |
| LightX2V | 存在，**有 Ref2VA 專用版**（4 步 544p、8 步 768p） | ✅ 第一優先 |
| Cinematic V2 | 存在（TuTu_1018，2026-10-20，151MB，強度 0.85） | ✅ 值得試，強度先 0.5～0.7 |
| Motion Speed Slider | 存在（Civitai make676767；另有 RunningHub 1.1） | △ 正值加快、負值放慢；對話鏡頭效益不明 |
| Acceleration Slider | 存在，但是「動作爆發力」，**不是步數加速** | ❌ 名字誤導，與本片無關 |
| H3 Camera Motion（Tripod） | 存在 `camera_motion_h3`，但**沒有 tripod／static 類別** | ❌ 不能鎖鏡頭；要推軌時再用 |
| High Contrast Daylight | **查無** | ❌ 而且方向相反（本片要陰天柔光） |
| Anamorphic Lens | **查無** | ❌ |

## 三、可用 LoRA 的分層地圖（只列與本片相關者）

| 層次 | 名稱 | 支援 Ref2VA | 大小 | 授權 | 解決本片哪個問題 |
|---|---|---|---|---|---|
| **A 步數／身份保持** | LightX2V Ref2VA 8 步 v1.0（768p） | ✅ 專用 | 約 1.9GB | Apache-2.0 | **N1 撞肩換臉**：ComfyUI 官方文件指出 4 步時參考圖約束較弱，8 步可能守得住臉 |
| A | 阿里 PAI Acc LoRA（PDD）Ref2VA 版 | ✅ 專用 | 約 1.4～1.7GB | H3 社群授權 | 同上；但要裝專用節點，排第二 |
| **B 畫質質感** | Cinematic V2（TuTu_1018） | 未標示 | 151MB | 商用僅 Rent | AI 塑膠膚、過銳 |
| B | fal Realism People | r2v | 約 125MB | 隨 H3 授權 | 近景臉、膚質；**會加手持感**，與鎖鏡頭衝突 |
| **C 動作** | Motion Adapter（MATLOWAI） | ✅ | 63MB | MIT | 動作過度生成；對話鏡頭 0.45、身份有問題 0.30 |
| C | Combat_V2／Motion_Repair_V2 | 未標示 | 已下載 | 未標示 | 已實測（推擠有效、救不了走位） |
| **D 運鏡** | Camera Shake Amplitude Slider（負權重） | 未標示 | 4MB | 要署名 | 鏡頭偷偷晃動／推近；Preview 版，只有 32 次下載 |
| **E 速度** | Speed Slider（±2） | 未標示 | 4～10MB | 未標示 | 優先度低 |

**不投入**：TaoMate、Acceleration Slider、Natural Face & Speech（t2v 訓練、英文語音、不可衍生）、SparseRef15（整個 20GB checkpoint，16GB 顯卡放不下）。

## 四、實驗方案（照優先順序；每組都是「同首幀、同 seed、同提示詞，只換 LoRA」）

### 實驗 1：步數與身份保持（最優先，會影響之後所有鏡頭的預設值）
> ✅ 2026-10-23 已用 DMAD 8 步／0.8 解決（見 `10_影片品質實驗.md` 第 1 階段），LightX2V 未測；之後若要比，用 `tools/h3_ab.py` 加自訂變體。
- 測試鏡：**N1 撞肩**（換臉問題）、**S22 老師近景對白**（嘴型）
- 組別：A＝DMAD 4 步（現行）｜B＝LightX2V Ref2VA 8 步｜C＝不加速 14 步（官方建議參考圖要守得住用 20～25 步，14 步當上限參考）
- 看：撞上瞬間臉有沒有換人、嘴型、音質、每鏡秒數
- 決策：B 若明顯守住臉、時間可接受 → 改成全片預設，**再**開始整片重跑

### 實驗 2：寫實質感
- 測試鏡：S18（老師近景）、S03（大頭近景）
- 組別：無｜Cinematic V2 0.5｜Cinematic V2 0.8｜fal Realism 0.7
- 看：膚質、與首幀長相差距、有沒有加手持晃動

### 實驗 3：動作與鏡頭穩定
- 測試鏡：S12（老師走到門口，曾鏡頭推近）、N1
- 組別：無｜Motion Adapter 0.45｜Camera Shake Slider −3｜兩者合用
- 看：鏡頭有沒有漂移、身份是否穩定

### 實驗 4（選做）：速度 Slider
- 測試鏡：S21（大頭答不出來）、S27（西瓜放下手）
- 組別：0｜−2｜+2

## 五、執行前提
- 下載量：實驗 1 約 1.9GB；實驗 2～3 合計約 350MB。D 槽空間足夠。
- Civitai 上的檔案（Cinematic V2、Camera Shake Slider）部分需要登入才能下載，**帳號登入由使用者自己操作**；HuggingFace 上的可直接下載。
- 未標示授權的檔案只在本機使用、不轉發；上 YouTube 營利前另讀授權。
- 時間：每組 H3 約 6～10 分鐘（8 步、14 步會更久），實驗 1 約 1 小時，實驗 2～3 各約 1 小時。

## 六、和「換背景整片重拍」的關係
實驗 1 的結果會決定 H3 的預設步數。**建議先做實驗 1，再整片重跑**，避免跑完 38 鏡才發現要換設定再跑一次。

## 來源（主要）
- [ComfyUI 官方 H3 文件](https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native)｜[LightX2V Ref2VA 8 步](https://comfyui-wiki.com/en/news/2026-09-04-minimax-h3-turbo-ref2v-8step)｜[PDD Acc LoRA](https://comfyui-wiki.com/zh/news/2026-08-26-minimax-h3-pdd-acc-lora)
- [Cinematic V2](https://civitai.com/models/2890588)｜[fal Realism People](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA)｜[Motion Adapter](https://comfyui-wiki.com/ja/news/2026-08-25-minimax-h3-motion-adapter)
- [Camera Shake Slider](https://civitai.com/models/3003926)｜[camera_motion_h3](https://civitai.com/models/2914784)｜[Speed Slider](https://civitai.com/models/2985458)｜[Turbo 合集](https://civitai.com/models/2837571)
- [HF 討論：遠景臉變形](https://huggingface.co/Comfy-Org/MiniMax-H3/discussions/30)｜[bbs.monster speed slider 說明](https://bbs.monster/thread-5182-1-1.html)
