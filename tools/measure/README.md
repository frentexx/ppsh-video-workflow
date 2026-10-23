# 影片一致性量測工具（2026-10-23）

AI 生成影片的「把關尺」：用數字抓出換臉、背景不像實景、鏡頭之間不一致，不靠肉眼也不花 LLM token。
**工具負責抓錯，人負責判斷好不好看**——它不會評美醜、演技，也抓不到「窗上是抿石子還是紅磚」這種細節。

| 程式 | 量什麼 | 用到的模型 |
|---|---|---|
| `facecheck.py` | 人臉身份一致性：影片每一格的臉 vs 首幀 | YuNet（找臉）＋SFace（臉部特徵，128 維）；cosine ≥ 0.363 視為同一人 |
| `bgcheck.py` | 背景一致性：遮掉人物後比場景 | DINOv2-base（場景特徵）＋rembg birefnet-portrait（人物遮罩） |

## 安裝（LIB-office 已裝在 `D:\AI\facecheck\`）

把本資料夾的 `facecheck.py`、`bgcheck.py` 複製到 `D:\AI\facecheck\`（模型放它底下的 `models\`；或用環境變數 `FACECHECK_MODELS` 指定）。`tools/h3_ab.py`、`tools/bg_inpaint.py` 預設就去 `D:\AI\facecheck\` 找，換位置時設 `FACECHECK`、`PY_FACECHECK` 環境變數。以下指令的 `python` 都是指 `D:\AI\facecheck\venv\Scripts\python.exe -X utf8`。

```
uv venv D:\AI\facecheck\venv --python 3.12
uv pip install --python D:\AI\facecheck\venv\Scripts\python.exe "opencv-python<5" numpy matplotlib "rembg[cpu]" pillow transformers
uv pip install --python D:\AI\facecheck\venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cpu
```
- 模型放 `D:\AI\facecheck\models\`：`face_detection_yunet_2023mar.onnx`、`face_recognition_sface_2021dec.onnx`（從 opencv_zoo 下載，**SFace 要用 media.githubusercontent.com 網址**，GitHub raw 會被截斷成 25MB，完整是 38.7MB）。
- opencv-python 5.0 讀不了 SFace → 一定要 `<5`。
- DINOv2、rembg 模型第一次執行自動下載（rembg birefnet 約 973MB）。
- 全部 CPU 就能跑，不佔 GPU；可以在 H3 生成時同時跑。

## 用法

```
# 換臉檢查：首幀 vs 一支或多支影片（同一鏡不同設定可一起比）
python facecheck.py out/first/N1.png out/h3/N1/clip.mp4 --out 結果資料夾

# 首幀背景像不像實景照
python bgcheck.py ref --images "out/first/S*.png" --refs 教室.jpg 走廊.jpg --masks out/bg_inpaint --out 結果資料夾

# 同場景鏡頭之間背景一不一致（輸出熱度圖 matrix.png）
python bgcheck.py matrix --images out/first/S03.png out/first/S06.png ... --masks out/bg_inpaint --out 結果資料夾

# 影片中背景有沒有漂移（抓偷換場景、鏡頭推近）
python bgcheck.py video --videos out/h3/S12/clip.mp4 --out 結果資料夾
```

## 怎麼讀結果
- **facecheck**：`summary.json` 每個人的「最低／平均／低於門檻秒數」＋曲線圖。換臉會在曲線上出現明顯下降。側臉、低頭時分數本來就會降，要看圖判斷。
- **bgcheck ref**：0.75 以上算接近實景；v6（AI 想像教室）平均 0.66 → v7（實景重繪）0.76。
- 臉太小（遠景、小於 40×40 像素）會被跳過，「找不到臉比例」會變高。

## 已驗證
- v6 的 N1 撞肩：曲線在 2.2 秒後掉到 0.27，與使用者肉眼看到的換臉時間一致。
- v6 vs v7 首幀：教室 25 鏡中 23 鏡變高，手部特寫從 0.31 升到 0.75。

## 什麼時候跑（新片 SOP 的兩個量測關卡）
- **首幀後**：`bgcheck.py ref`（背景像不像實景，目標 ≥ 0.75）＋`bgcheck.py matrix`（同場景各鏡一致）
- **H3 後**：每一鏡 `facecheck.py`（有沒有換臉）＋`bgcheck.py video`（有沒有偷換場景、鏡頭推近）
- 數字只負責抓錯；過關後仍要人看成片

## 其他用途
- 角色 LoRA 選步數：各步數樣圖 vs 本人照片，取平均最高的。
- 候選首幀自動排名。

## 授權
SFace、YuNet、DINOv2：Apache-2.0；rembg、BiRefNet：MIT。程式本身可分享；分享時不要附學生或本人照片。若改用 insightface 模型要注意其**限非商用**。
