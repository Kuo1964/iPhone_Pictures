#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
個人相片自動轉檔與增量歸檔腳本 (organize_photos.py) - 檔案無變更保護版
核心原則：
1. 嚴禁修改 Photos/ 目錄下任何既有照片的檔案名稱與檔案內容。
2. 嚴禁移動或刪除 Photos/ 目錄下的任何既有目錄與檔案。
3. 僅針對 Photos/ 目錄以外的新上傳照片進行無損轉檔與歸檔。
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

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "Photos"
DB_FILE = BASE_DIR / "photos_db.json"
GEO_CACHE_FILE = BASE_DIR / "geo_cache.json"

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
    """使用 macOS mdls 提取圖片中詳細的 EXIF Metadata (唯讀)"""
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
    """僅針對 Photos/ 外的 HEIC 新照片轉檔"""
    jpeg_path = heic_path.with_suffix(".jpeg")
    if jpeg_path.exists() and jpeg_path != heic_path:
        jpeg_path = heic_path.with_name(f"{heic_path.stem}_converted.jpeg")

    print(f"🔄 轉換新 HEIC: {heic_path.name} -> {jpeg_path.name}")
    try:
        cmd = ["sips", "-s", "format", "jpeg", str(heic_path), "--out", str(jpeg_path)]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if jpeg_path.exists() and jpeg_path.stat().st_size > 0:
            heic_path.unlink()
            return jpeg_path
    except Exception as e:
        print(f"❌ 轉換失敗 ({heic_path.name}): {e}")
    return None

def process_photos(source_dir=BASE_DIR):
    """
    掃描與建立索引
    【嚴禁修改 Photos/ 目錄內既有檔案名稱與內容】
    """
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
                        old_people_map[item["id"]] = item["people"]
        except Exception:
            pass

    # 1. 處理 Photos/ 外的全新 HEIC 檔案
    new_heic_files = [f for f in BASE_DIR.rglob("*") 
                      if f.is_file() and f.suffix.lower() in {".heic"} and PHOTOS_DIR not in f.parents]
    for heic in new_heic_files:
        convert_heic_to_jpeg(heic)

    # 2. 區分全新照片與既有照片
    valid_exts = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    all_jpegs = [f for f in BASE_DIR.rglob("*") if f.is_file() and f.suffix in valid_exts]
    
    new_photos = [f for f in all_jpegs if PHOTOS_DIR not in f.parents]
    existing_photos = [f for f in all_jpegs if PHOTOS_DIR in f.parents]
    
    print(f"📁 發現 {len(new_photos)} 張全新上傳照片，{len(existing_photos)} 張既有照片 (100% 保持原檔名稱與內容不修改)。")
    
    # 對全新照片移入 Photos/ (保留原檔名)
    for img_path in new_photos:
        meta = get_metadata_via_mdls(img_path)
        creation_date = meta["creation_date"]
        lat = meta["latitude"]
        lon = meta["longitude"]

        year_str = "未排序"
        month_str = "未排序"
        if creation_date:
            parts = creation_date.split(" ")
            if len(parts) >= 2:
                d_parts = parts[0].split("-")
                if len(d_parts) == 3:
                    year_str = d_parts[0]
                    month_str = f"{d_parts[0]}-{d_parts[1]}"

        location_name = reverse_geocode(lat, lon)
        target_dir = PHOTOS_DIR / year_str / f"{month_str}_{location_name}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / img_path.name
        if target_path.exists():
            target_path = target_dir / f"{img_path.stem}_{int(time.time())}{img_path.suffix}"
            
        img_path.rename(target_path)

    # 3. 讀取 Photos/ 既有內容構建/更新索引 (100% 唯讀，原檔名與內容完全不變)
    final_jpegs = [f for f in PHOTOS_DIR.rglob("*") if f.is_file() and f.suffix in valid_exts]
    photos_db_list = []

    for img_path in final_jpegs:
        rel_path = str(img_path.relative_to(BASE_DIR))
        photo_id = hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]
        
        meta = get_metadata_via_mdls(img_path)
        creation_date = meta["creation_date"]
        lat = meta["latitude"]
        lon = meta["longitude"]

        parent_dir_name = img_path.parent.name
        year_dir_name = img_path.parent.parent.name if img_path.parent.parent != PHOTOS_DIR else "未排序"
        year_str = year_dir_name if year_dir_name.isdigit() else "未排序"
        
        location_name = "未知地點"
        if "_" in parent_dir_name:
            location_name = parent_dir_name.split("_", 1)[1]
        else:
            location_name = reverse_geocode(lat, lon)

        date_display = "未知日期"
        if creation_date:
            parts = creation_date.split(" ")
            if len(parts) >= 2:
                d_parts = parts[0].split("-")
                if len(d_parts) == 3:
                    date_display = f"{d_parts[0]}-{d_parts[1]}-{d_parts[2]} {parts[1]}"
                    if year_str == "未排序":
                        year_str = d_parts[0]

        people_tags = old_people_map.get(photo_id) or old_people_map.get(img_path.name) or []

        photos_db_list.append({
            "id": photo_id,
            "filename": img_path.name, # 100% 保留原本檔案名稱
            "path": rel_path,
            "year": year_str,
            "month": parent_dir_name.split("_")[0] if "_" in parent_dir_name else "未排序",
            "date": date_display,
            "location": location_name,
            "latitude": lat,
            "longitude": lon,
            "people": people_tags
        })

    # 更新 photos_db.json
    db_data = {
        "photos": photos_db_list,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 索引構建完畢！共索引 {len(photos_db_list)} 張照片。所有原檔名稱與內容 100% 保留未改動。")

if __name__ == "__main__":
    process_photos()
