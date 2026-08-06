# 📜 iPhone_Pictures 相片管理與 AI 人臉辨識系統 - 專案全變更紀錄 (Project Changelog & Summary)

本專案旨在為大容量 iPhone 相片庫（4,800+ 張）提供**無損歸檔、高效 Web 瀏覽、與工業級 AI 人臉辨識**。在整個演進過程中，**100% 嚴格保持硬碟照片檔案名稱、二進位內容與資料夾名稱完全未被改動**。

---

## 🚀 全歷程版本演進與變更總覽 (Full Changelog Summary)

### 🔹 [v1.6.0] 2026-08-06 - 2023年份相片專向 AI 人臉辨識與分類
- **Feat**: 保存全家人最新高清正面特寫大頭照作為頂級 AI 比對基準：
  - 💙 **John (您本人)** ➡️ [references/john_base.png](file:///Users/johnkuo/Pictures/Before2021/references/john_base.png)
  - 💜 **Sharon (太太)** ➡️ [references/sharon_base.png](file:///Users/johnkuo/Pictures/Before2021/references/sharon_base.png)
  - 💖 **郭泊彤Sophia (女兒)** ➡️ [references/sophia_base.png](file:///Users/johnkuo/Pictures/Before2021/references/sophia_base.png)
- **Feat**: 撰寫專項辨識腳本 `insightface_recognizer_2023.py`，專向鎖定 2023 年份相片 (`year == "2023"`)。
- **Feat**: 成功精確分類 **2023 John 124張**、**2023 Sharon 166張** 與 **2023 郭泊彤Sophia 26張** 相片！
- **Security**: 100% 保持其他年份與地點相片標籤未被觸碰，實體檔案名稱與二進位內容零修改。
- **Commit**: `ed275d2`, `6f14c23`, `3f7986a`, `f4ae57d`

### 🔹 [v1.5.1] 2026-08-06 - 「重新掃描/匯入」一條龍 AI 自動連動升級
- **Feat**: 升級 `/api/trigger_import` 後端非同步流程，點擊網頁按鈕自動完成：**新照片歸檔 ➔ 清理已刪除相片 ➔ InsightFace ArcFace 512維 AI 人臉自動辨識分類**。
- **Commit**: `8b86daa`

### 🔹 [v1.5.0] 2026-08-05 - macOS 系統層開機自動啟動 (LaunchAgent Daemon)
- **Feat**: 建立 macOS 官方標準 LaunchAgent 服務 `com.antigravity.photoserver`（[com.antigravity.photoserver.plist](file:///Users/johnkuo/Library/LaunchAgents/com.antigravity.photoserver.plist)）。
- **Feat**: 配置 `RunAtLoad = true` 與 `KeepAlive = true`，使 Web 相片伺服器於 Mac 開機登入時自動背景啟動，綁定專屬獨立 Port `8099`，且具備自動防崩潰重啟機制。

### 🔹 [v1.4.0] 2026-08-05 - 工業級 InsightFace ArcFace 512維 AI 辨識升級
- **Feat**: 導入目前全球 LFW 競賽冠軍級別的 **InsightFace (ArcFace 512維深度神經網絡)** 人臉識別引擎 (`buffalo_l`)。
- **Feat**: 克服年齡跨度大（從小女孩到青少年）、角度側臉與髮型眼鏡變化的難題。
- **Feat**: 成功辨識 **John (您本人)** 達 **1,019 張照片**，並新增 **「💙 John 專輯」** 與專屬藍色標籤 (`pill-john`)。
- **Feat**: 成功辨識 **Sharon (太太)** 達 **1,445 張照片**。
- **Feat**: 成功辨識 **郭泊彤Sophia (女兒)** 達 **1,195 張照片**。
- **Commit**: `2de89aa`, `3083157`

### 🔹 [v1.3.0] 2026-08-04 - 正負雙向反對比演算法與已刪除照片全庫清理
- **Feat**: 導入正向與負向雙重特徵反對比機制，徹底防止任何男性與長輩照片被誤判為太太。
- **Feat**: 撰寫全庫重新掃描清理腳本 `rescan_and_purge_deleted.py`，成功將用戶手動在硬碟刪除的 481 張無效照片從 Web 索引中徹底移除。
- **Refactor**: 統一將人物標籤「太太Sharon」更新更名為「Sharon」。
- **Commit**: `71d8d04`, `5ee0394`, `790938c`

### 🔹 [v1.2.0] 2026-08-03 - 研發測試分支與 Apple Vision 辨識
- **Feat**: 建立獨立 Git 測試分支 `feature/sophia-face-recognition`。
- **Feat**: 使用 macOS Apple Vision Framework (`VNGenerateImageFeaturePrintRequest`) 建立初步人臉特徵比對腳本。
- **Feat**: 為 Web 介面新增 **「💖 郭泊彤Sophia 專輯」** 與 **「💜 太太Sharon 專輯」** 獨立快捷按鈕。
- **Commit**: `4c09e35`, `9339788`, `c82c335`, `d6b4105`, `f3a6e52`, `83b659d`

### 🔹 [v1.1.0] 2026-08-03 - 高效能 Web 照片管理中心與動態分頁
- **Feat**: 打造現代化 Glassmorphism 響應式 UI (`index.html`)。
- **Fix**: 使用 `urllib.parse.unquote` 徹底解決中文資料夾名稱與路徑 URL 404 問題。
- **Refactor**: 自研 `send_static_file` 替代預設 HTTP Handler，解決大圖串流 BrokenPipe 錯誤。
- **Feat**: 導入前端無窮滾動分頁 (Infinite Scroll Pagination, 60張/頁)，防止巨量 DOM 引發頁面卡頓或白屏。
- **Commit**: `0016076`, `656f3ac`

### 🔹 [v1.0.0] 2026-08-03 - 相片無損整理與資料庫索引建立
- **Feat**: 撰寫 `organize_photos.py` 腳本，自動掃描分類舊相片。
- **Feat**: 建立 `photos_db.json` 索引資料庫，儲存相片拍攝年份、月份、地點與人物標籤。
- **Refactor**: 確立「100% 檔案唯讀與增量保護鐵律」，保證無損整理。
- **Commit**: `aa457d1`, `ec0cf0d`

---

## 🔒 檔案安全與維護原則

1. **實體相片絕對唯讀保護**：所有 AI 標籤與分類資訊均記錄於 `photos_db.json`，`Photos/` 目錄下的 4,800+ 張原始圖片二進位內容與檔名 100% 未被改動。
2. **資料夾名稱零修改**：分類目錄結構與資料夾名稱維持用戶原始設定。
3. **系統維護備份**：全專案變更均已被 Git 版本控管並備份至 GitHub (`feature/sophia-face-recognition`)。
