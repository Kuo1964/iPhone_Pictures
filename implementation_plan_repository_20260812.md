# 📋 JSON 資料庫存取層解耦 (PhotoRepository 深層模組) 重構計畫 (Implementation Plan 2026-08-12)

本計畫旨在解決目前 `server.py`、`face_recognizer.py` 與 `organize_photos.py` 中直接讀寫 `photos_db.json` 導致的架構摩擦問題。透過建立**深層模組 `photo_repository.py` (PhotoRepository)**，將檔案 I/O、併發鎖 (ThreadLock) 與原子寫入 (Atomic Write) 徹底封裝，提供極簡且強固的資料存取介面。

---

## ⚠️ User Review Required (用戶審核項目)

> [!IMPORTANT]
> **本重構計畫包含以下核心設計：**
> 1. **深層模組封裝**：建立 `PhotoRepository` 類別，隱藏所有 `json.load()` 與 `json.dump()` 檔案操作細節。
> 2. **併發與安全防護 (Concurrency & Safety)**：導入 `threading.Lock()` 防止多執行緒同時寫入衝突，並採用**原子寫入機制 (Atomic Write: 寫入 `.tmp` 檔案後經 `os.replace` 覆蓋)**，徹底防止系統崩潰導致 `photos_db.json` 損壞。
> 3. **100% 唯讀保障**：實體照片檔名、內容與資料夾名稱 100% 保持零改動。
> 4. **歷史歸檔**：計畫與修復成果將分別標註日期歸檔存檔。

---

## 🛠️ 擬議變更內容 (Proposed Changes)

### 1. 建立 PhotoRepository 深層模組

#### [NEW] [photo_repository.py](file:///Users/johnkuo/Pictures/Before2021/photo_repository.py)
- **類別設計**：`PhotoRepository(db_path="photos_db.json")`
- **提供 API 介面**：
  - `get_all_photos() -> list[dict]`：讀取並傳回所有相片紀錄。
  - `get_photo_by_id(photo_id: str) -> dict | None`：依 ID 尋找相片。
  - `upsert_photos(new_photos: list[dict]) -> int`：增量插入或更新相片索引。
  - `update_people_tags(matches_map: dict[str, list[str]]) -> int`：批量高效更新 John, Sharon, Sophia 人物標籤。
  - `delete_photos_by_path(deleted_paths: list[str]) -> int`：刪除無效照片紀錄。
- **內部實作機制**：
  - 封裝 `_load()` 與 `_save_atomic()`。
  - `_save_atomic()` 先寫入 `photos_db.json.tmp`，完成後調用 `os.replace` 進行原子性更換。
  - 內建 `threading.Lock()` 確保安全。

---

### 2. 重構各呼叫模組 (Refactoring Call Sites)

#### [MODIFY] [server.py](file:///Users/johnkuo/Pictures/Before2021/server.py)
- 將 API Handler 中直接讀寫 JSON 的邏輯替換為 `PhotoRepository` 的高階 API 呼叫。

#### [MODIFY] [face_recognizer.py](file:///Users/johnkuo/Pictures/Before2021/face_recognizer.py)
- 人臉比對完成後，由原本的直接 JSON 寫入改為調用 `repo.update_people_tags(matches_map)` 進行批量原子更新。

#### [MODIFY] [organize_photos.py](file:///Users/johnkuo/Pictures/Before2021/organize_photos.py)
- 相片歸檔完成後，改為調用 `repo.upsert_photos()` 寫入索引。

---

## 🧪 驗證計畫 (Verification Plan)

### 單元測試與自動化測試
1. 為 `photo_repository.py` 撰寫專屬單元測試 `test_photo_repository.py`：
   - 測試多執行緒併發讀寫。
   - 測試原子寫入 (Atomic Write) 中斷防禦。
   - 測試 `update_people_tags` 的正確性。
   - 執行命令：`python3 -m unittest test_photo_repository.py`

### 手動與一條龍驗證
1. 執行 `python3 face_recognizer.py` 驗證標籤可經由 `PhotoRepository` 原子更新。
2. 測試 `/api/photos` 與 `/api/trigger_import` 端點運作正常。

---

## 📜 歷史歸檔計畫 (Archiving Protocol)
- **實施計畫存檔**：`implementation_plan_repository_20260812.md`
- **成果報告存檔**：`walkthrough_repository_20260812.md`
- 報告將永久標註日期 `2026-08-12` 歸檔保存。
