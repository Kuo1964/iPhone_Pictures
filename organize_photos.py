#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
個人相片自動轉檔與分類腳本 (organize_photos.py) - 全面重新整理版
功能：
1. 深度掃描工作區內的所有照片（包含 Photos 內的子目錄）。
2. 將 HEIC/HEIF 照片無損轉換為 JPEG 格式，轉換成功後自動刪除原 HEIC 檔案。
3. 提取 EXIF 拍攝時間與 GPS 座標，透過逆地理編碼取得中文地點名稱。
4. 重新修正與歸檔所有照片至「Photos/YYYY/YYYY-MM_地點/」兩層資料夾結構中。
5. 清理空白資料夾，並重新生成/更新 photos_db.json 索引資料庫。
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

# 配置設定
BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "Photos"
DB_FILE = BASE_DIR / "photos_db.json"
GEO_CACHE_FILE = BASE_DIR / "geo_cache.json"

# 地理逆編碼快取
geo_cache = {}
if GEO_CACHE_FILE.exists():
    try:
        with open(GEO_CACHE_FILE, "r", encoding="utf-8") as f:
            geo_cache = json.load(f)
    except Exception:
        geo_cache = {}

def save_geo_cache():
    try:
        with open(GEO_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(geo_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告：無法儲存地理快取: {e}")

def get_metadata_via_mdls(file_path):
    """使用 macOS mdls 提取圖片中詳細的 EXIF Metadata"""
    try:
        cmd = ["mdls", "-raw", 
               "-attr", "kMDItemContentCreationDate", 
               "-attr", "kMDItemLatitude", 
               "-attr", "kMDItemLongitude", 
               str(file_path)]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        parts = output.split("\x00")
        
        creation_date = parts[0] if len(parts) > 0 and parts[0] != "(null)" else None
        latitude_str = parts[1] if len(parts) > 1 and parts[1] != "(null)" else None
        longitude_str = parts[2] if len(parts) > 2 and parts[2] != "(null)" else None

        latitude = float(latitude_str) if latitude_str else None
        longitude = float(longitude_str) if longitude_str else None

        return {
            "creation_date": creation_date,
            "latitude": latitude,
            "longitude": longitude
        }
    except Exception:
        return {"creation_date": None, "latitude": None, "longitude": None}

def reverse_geocode(lat, lon):
    """根據緯度經度獲取中文地點名稱"""
    if lat is None or lon is None:
        return "未知地點"
    
    key = f"{round(lat, 2)},{round(lon, 2)}"
    if key in geo_cache:
        return geo_cache[key]
    
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&accept-language=zh-TW"
    headers = {"User-Agent": "AntigravityPhotoOrganizer/1.0"}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                address = data.get("address", {})
                
                city = (address.get("city") or 
                        address.get("town") or 
                        address.get("county") or 
                        address.get("state") or 
                        address.get("country") or 
                        "未知地點")
                
                city_clean = city.replace("Special Administrative Region", "").replace("Province", "").strip()
                geo_cache[key] = city_clean
                save_geo_cache()
                time.sleep(1)
                return city_clean
    except Exception:
        pass
    
    # 預設離線主要地區判斷 fallback
    if 21.8 <= lat <= 25.3 and 119.5 <= lon <= 122.1:
        if lat > 24.8:
            location = "台北"
        elif lat > 24.3:
            location = "新竹"
        elif lat > 23.5:
            location = "彰化"
        else:
            location = "高雄"
        geo_cache[key] = location
        save_geo_cache()
        return location

    return "未知地點"

def convert_heic_to_jpeg(heic_path):
    """將 HEIC 檔案轉為 JPEG 格式並在成功後自動刪除原檔"""
    jpeg_path = heic_path.with_suffix(".jpeg")
    if jpeg_path.exists() and jpeg_path != heic_path:
        jpeg_path = heic_path.with_name(f"{heic_path.stem}_converted.jpeg")

    print(f"🔄 轉換中: {heic_path.name} -> {jpeg_path.name}")
    try:
        cmd = ["sips", "-s", "format", "jpeg", str(heic_path), "--out", str(jpeg_path)]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if jpeg_path.exists() and jpeg_path.stat().st_size > 0:
            print(f"  └─ 轉換成功，移除原 HEIC 檔案: {heic_path.name}")
            heic_path.unlink()
            return jpeg_path
    except Exception as e:
        print(f"❌ 轉換失敗 ({heic_path.name}): {e}")
    return None

def remove_empty_folders(path):
    """遞迴清理空資料夾"""
    if not path.is_dir():
        return
    for sub in list(path.iterdir()):
        if sub.is_dir():
            remove_empty_folders(sub)
    try:
        if not list(path.iterdir()) and path != PHOTOS_DIR and path != BASE_DIR:
            path.rmdir()
            print(f"🧹 清理空資料夾: {path.relative_to(BASE_DIR)}")
    except Exception:
        pass

def process_photos(source_dir=BASE_DIR):
    """深度掃描並重新整理分類所有相片"""
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 載入原有資料庫以維護人物標籤
    old_people_map = {}
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                old_db = json.load(f)
                for item in old_db.get("photos", []):
                    if item.get("people"):
                        old_people_map[item["filename"]] = item["people"]
        except Exception:
            pass

    # 1. 第一步：遞迴找出所有 HEIC 檔案並轉檔
    print("🔍 進行全盤掃描與 HEIC 轉檔檢測...")
    heic_files = list(BASE_DIR.rglob("*.heic")) + list(BASE_DIR.rglob("*.HEIC"))
    for heic in heic_files:
        convert_heic_to_jpeg(heic)

    # 2. 第二步：遞迴找出所有 JPEG 相片進行拍攝資訊解析與重新歸檔
    valid_exts = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    all_jpegs = [f for f in BASE_DIR.rglob("*") if f.is_file() and f.suffix in valid_exts]
    print(f"📁 開始重新比對與整理共 {len(all_jpegs)} 張 JPEG 相片...")
    
    photos_db_list = []
    moved_count = 0

    for img_path in all_jpegs:
        meta = get_metadata_via_mdls(img_path)
        creation_date = meta["creation_date"]
        lat = meta["latitude"]
        lon = meta["longitude"]

        year_str = "未排序"
        month_str = "未排序"
        date_display = "未知日期"
        
        if creation_date:
            parts = creation_date.split(" ")
            if len(parts) >= 2:
                d_parts = parts[0].split("-")
                if len(d_parts) == 3:
                    year_str = d_parts[0]
                    month_str = f"{d_parts[0]}-{d_parts[1]}"
                    date_display = f"{d_parts[0]}-{d_parts[1]}-{d_parts[2]} {parts[1]}"

        location_name = reverse_geocode(lat, lon)
        
        # 正確目標路徑: Photos/YYYY/YYYY-MM_地點/filename.jpeg
        target_dir = PHOTOS_DIR / year_str / f"{month_str}_{location_name}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / img_path.name
        
        # 若路徑不符，進行重新歸檔移動
        if img_path.resolve() != target_path.resolve():
            if target_path.exists():
                target_path = target_dir / f"{img_path.stem}_{int(time.time())}{img_path.suffix}"
            img_path.rename(target_path)
            moved_count += 1

        rel_path = str(target_path.relative_to(BASE_DIR))
        photo_id = hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]
        
        # 保留人物標籤
        people_tags = old_people_map.get(target_path.name, [])

        photos_db_list.append({
            "id": photo_id,
            "filename": target_path.name,
            "path": rel_path,
            "year": year_str,
            "month": month_str,
            "date": date_display,
            "location": location_name,
            "latitude": lat,
            "longitude": lon,
            "people": people_tags
        })

    # 3. 第三步：清理被移空的舊資料夾
    remove_empty_folders(PHOTOS_DIR)

    # 4. 第四步：重新寫入 photos_db.json
    db_data = {
        "photos": photos_db_list,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"✨ 重新整理完畢！共歸檔/校正 {moved_count} 張相片位置。")
    print(f"📊 目前資料庫總計 {len(photos_db_list)} 張相片紀錄。")

if __name__ == "__main__":
    process_photos()
