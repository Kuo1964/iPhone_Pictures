# 📋 EXIF 解析與地理解碼轉接器 (MetadataExtractor & GeocoderAdapter) 重構計畫 (Implementation Plan 2026-08-12)

本計畫旨在解決目前 `organize_photos.py` 中直接硬編碼 macOS `mdls` CLI subprocess 呼叫與直呼 OpenStreetMap 網路 API 所導致的架構摩擦。透過導入**轉接器模式 (Adapter Pattern)**，建立 `metadata_adapter.py`，將作業系統依賴與網路通訊徹底解耦，提升代碼跨平台性與單元測試獨立性。

---

## ⚠️ User Review Required (用戶審核項目)

> [!IMPORTANT]
> **本重構計畫包含以下核心設計：**
> 1. **MetadataExtractor 轉接器設計**：抽象化 EXIF 拍攝時間與 GPS 經緯度提取介面；實作 `MacOSMetadataExtractor` (生產環境) 與 `MockMetadataExtractor` (測試環境)。
> 2. **GeocoderAdapter 地理轉接器設計**：抽象化反向地理解碼介面；實作 `OSMGeocoderAdapter` (網路 API) 與 `OfflineFallbackGeocoder` (台灣區域演算法及快取)。
> 3. **100% 離線單元測試能力**：透過 Mock Adapter 使單元測試 100% 不需依賴實體 OS 命令或網際網路連線即可極速執行。
> 4. **100% 唯讀保障**：實體照片檔名、內容與資料夾名稱 100% 保持零改動。
> 5. **歷史歸檔**：計畫與修復成果將分別標註日期歸檔存檔。

---

## 🛠️ 擬議變更內容 (Proposed Changes)

### 1. 建立 MetadataAdapter 深層模組與單元測試

#### [NEW] [metadata_adapter.py](file:///Users/johnkuo/Pictures/Before2021/metadata_adapter.py)
- **類別設計**：
  - `BaseMetadataExtractor` (抽象類別)：定義 `extract_metadata(image_path) -> dict`
  - `MacOSMetadataExtractor`：封裝 `mdls` subprocess 呼叫。
  - `MockMetadataExtractor`：供單元測試使用。
  - `BaseGeocoder` (抽象類別)：定義 `get_location_name(lat, lon) -> str`
  - `OfflineFallbackGeocoder`：封裝全台主要區域邊界判斷與 JSON 地理快取。
  - `OSMGeocoderAdapter`：封裝 OpenStreetMap HTTP 請求。
  - `MockGeocoder`：供單元測試使用。

#### [NEW] [test_metadata_adapter.py](file:///Users/johnkuo/Pictures/Before2021/test_metadata_adapter.py)
- 撰寫轉接器專屬單元測試，驗證 Mock 提取、離線地理解碼與邊界條件。

---

### 2. 重構 organize_photos.py (Refactoring Call Sites)

#### [MODIFY] [organize_photos.py](file:///Users/johnkuo/Pictures/Before2021/organize_photos.py)
- 重構 `get_photo_metadata()` 與 `get_location_from_coords()`：改經由 `default_metadata_extractor` 與 `default_geocoder` 進行數據提取。

---

## 🧪 驗證計畫 (Verification Plan)

### 單元測試與自動化測試
1. 執行專屬單元測試：`python3 -m unittest test_metadata_adapter.py`
2. 驗證在離線無網環境下單元測試 100% 綠燈。

### 手動與端到端驗證
1. 執行 `python3 organize_photos.py` 驗證相片歸檔與地點識別完全正常。
2. 驗證網頁相片數據點擊地點過濾完全正常。

---

## 📜 歷史歸檔計畫 (Archiving Protocol)
- **實施計畫存檔**：`implementation_plan_metadata_20260812.md`
- **成果報告存檔**：`walkthrough_metadata_adapter_20260812.md`
- 報告將永久標註日期 `2026-08-12` 歸檔保存。
