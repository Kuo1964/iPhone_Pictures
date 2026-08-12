#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全庫重新掃描與刪除相片清理腳本 (rescan_and_purge_deleted.py)
功能：
1. 重新檢查 Photos/ 目錄下所有相片。
2. 將使用者手動刪除、已不存在於硬碟上的相片從 photos_db.json 中徹底清除。
3. 100% 保持既有資料夾名稱不變，100% 保持既有相片檔名與內容不變。
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "Photos"
DB_FILE = BASE_DIR / "photos_db.json"

def purge_and_rescan():
    if not DB_FILE.exists():
        print("❌ 找不到 photos_db.json 資料庫！")
        return

    with open(DB_FILE, "r", encoding="utf-8") as f:
        db_data = json.load(f)

    original_photos = db_data.get("photos", [])
    print(f"📊 掃描前資料庫紀錄相片總數: {len(original_photos)} 張")

    valid_photos = []
    purged_count = 0

    # 1. 檢查並剔除硬碟上已不存在的相片
    for photo in original_photos:
        rel_path = photo.get("path")
        if rel_path:
            full_path = BASE_DIR / rel_path
            if full_path.exists() and full_path.is_file():
                valid_photos.append(photo)
            else:
                purged_count += 1
                print(f"🗑️ 已從Web清理移除不存在的相片: {rel_path}")

    # 2. 檢查 Photos/ 目錄下是否有硬碟上有但 DB 沒紀錄的新圖片 (保留資料夾名稱)
    existing_paths = {p["path"] for p in valid_photos}
    valid_exts = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    
    new_added_count = 0
    if PHOTOS_DIR.exists():
        for img_path in PHOTOS_DIR.rglob("*"):
            if img_path.is_file() and img_path.suffix in valid_exts:
                rel_path = str(img_path.relative_to(BASE_DIR))
                if rel_path not in existing_paths:
                    photo_id = hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]
                    
                    parent_dir_name = img_path.parent.name
                    year_dir_name = img_path.parent.parent.name if img_path.parent.parent != PHOTOS_DIR else "未排序"
                    year_str = year_dir_name if year_dir_name.isdigit() else "未排序"
                    
                    location_name = "未知地點"
                    if "_" in parent_dir_name:
                        location_name = parent_dir_name.split("_", 1)[1]

                    valid_photos.append({
                        "id": photo_id,
                        "filename": img_path.name,
                        "path": rel_path,
                        "year": year_str,
                        "month": parent_dir_name.split("_")[0] if "_" in parent_dir_name else "未排序",
                        "date": "未知日期",
                        "location": location_name,
                        "latitude": None,
                        "longitude": None,
                        "people": []
                    })
                    new_added_count += 1
                    print(f"✨ 發現未索引的本地相片並加入: {rel_path}")

    # 3. 儲存更新後的 photos_db.json
    db_data["photos"] = valid_photos
    db_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 重新掃描與清理完畢！")
    print(f"  ├─ 成功從 Web 移除已刪除照片: {purged_count} 張")
    print(f"  ├─ 補全索引新增照片: {new_added_count} 張")
    print(f"  └─ 目前 Web 保留有效照片總數: {len(valid_photos)} 張")
    print(f"  🔒 資料夾名稱 100% 保持原本完全未改動。")

if __name__ == "__main__":
    purge_and_rescan()
