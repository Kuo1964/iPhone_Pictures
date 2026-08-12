# 📋 HTTP Route 與非同步工作流解耦 (ImportPipeline 深層模組) 重構計畫 (Implementation Plan 2026-08-12)

本計畫旨在解決目前 `server.py` 的 `/api/trigger_import` Handler 中直接硬編碼 `threading.Thread` 匿名執行緒與順序步驟所導致的架構摩擦。透過建立**深層模組 `import_pipeline.py` (ImportPipeline)**，將多階段工作流排程、線程管理、狀態追蹤 (Status Tracking) 與例外捕獲徹底封裝。

---

## ⚠️ User Review Required (用戶審核項目)

> [!IMPORTANT]
> **本重構計畫包含以下核心設計：**
> 1. **深層工作流模組封裝**：建立 `ImportPipeline` 類別，隱藏多執行緒啟動與多階段執行的內部細節。
> 2. **狀態追蹤與即時查詢**：提供 `get_status()` API，維護任務狀態 (`idle`, `running`, `stage_1_organizing`, `stage_2_purging`, `stage_3_recognizing`, `completed`, `failed`) 與詳細日誌，徹底解決未知的背景執行狀態。
> 3. **例外安全防護**：全階段捕獲 Exception 並紀錄於狀態中，解決過去 Swallow Exception 的氣味。
> 4. **100% 唯讀保障**：實體照片檔名、內容與資料夾名稱 100% 保持零改動。
> 5. **歷史歸檔**：計畫與修復成果將分別標註日期歸檔存檔。

---

## 🛠️ 擬議變更內容 (Proposed Changes)

### 1. 建立 ImportPipeline 深層模組與單元測試

#### [NEW] [import_pipeline.py](file:///Users/johnkuo/Pictures/Before2021/import_pipeline.py)
- **類別設計**：`ImportPipeline()`
- **提供 API 介面**：
  - `start_import_async() -> bool`：非同步啟動一條龍匯入與 AI 人臉辨識工作流。
  - `get_status() -> dict`：傳回即時任務狀態 JSON（含階段名稱、開始時間、耗時、狀態碼、錯誤資訊）。
  - `run_import_sync() -> dict`：同步順序執行（供單元測試與 CLI 使用）。
- **內部實作機制**：
  - 封裝 Stage 1: 照片無損歸檔 (`organize_photos`) ➔ Stage 2: 已刪除照片清理 (`rescan_and_purge_deleted`) ➔ Stage 3: AI 人臉辨識 (`face_recognizer`)。
  - 內建 `threading.Lock()` 確保同一時間僅有一個匯入工作流在執行（防範重複觸發）。

#### [NEW] [test_import_pipeline.py](file:///Users/johnkuo/Pictures/Before2021/test_import_pipeline.py)
- 撰寫 Pipeline 單元測試，驗證狀態轉變、非同步鎖與例外捕獲。

---

### 2. 重構 server.py (Refactoring API Handler)

#### [MODIFY] [server.py](file:///Users/johnkuo/Pictures/Before2021/server.py)
- 重構 `/api/trigger_import` Handler：改簡化為單行呼叫 `default_pipeline.start_import_async()`。
- 新增 `/api/import_status` API 端點：供前端即時查詢背景匯入與 AI 辨識進度。

---

## 🧪 驗證計畫 (Verification Plan)

### 單元測試與自動化測試
1. 執行專屬單元測試：`python3 -m unittest test_import_pipeline.py`
2. 驗證非同步防重複觸發機制與狀態轉換。

### 手動與端到端驗證
1. 測試呼叫 API：`curl -X POST http://localhost:8099/api/trigger_import`
2. 測試查詢狀態 API：`curl http://localhost:8099/api/import_status`
3. 驗證 Web 介面上「重新掃描/匯入」運作完全正常。

---

## 📜 歷史歸檔計畫 (Archiving Protocol)
- **實施計畫存檔**：`implementation_plan_pipeline_20260812.md`
- **成果報告存檔**：`walkthrough_pipeline_20260812.md`
- 報告將永久標註日期 `2026-08-12` 歸檔保存。
