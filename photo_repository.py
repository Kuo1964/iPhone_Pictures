#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
iPhone_Pictures 相片資料庫存取層深層模組 (photo_repository.py)
特色：
1. 高內聚深層介面：隱藏 open() / json.load() / json.dump() 實作細節。
2. 併發防禦：內建 threading.Lock() 確保多執行緒讀寫安全。
3. 原子寫入防禦 (Atomic Write)：先寫入 .tmp 檔案，完成後經 os.replace 進行原子性更換，徹底防止崩潰損壞 DB。
4. 100% 唯讀保護實體相片檔案。
"""

import os
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

class PhotoRepository:
    def __init__(self, db_path: str = "photos_db.json"):
        self.base_dir = Path(__file__).resolve().parent
        self.db_path = self.base_dir / db_path
        self._lock = threading.Lock()

    def _load_data_unlocked(self) -> Dict[str, Any]:
        """無鎖讀取 JSON（內部使用）"""
        if not self.db_path.exists():
            return {"photos": []}
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ [PhotoRepository] 讀取 JSON 失敗: {e}")
            return {"photos": []}

    def _save_data_atomic_unlocked(self, data: Dict[str, Any]) -> bool:
        """原子寫入 JSON（內部使用：寫入 .tmp 後以 os.replace 更換）"""
        tmp_path = self.db_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.db_path)
            return True
        except Exception as e:
            print(f"❌ [PhotoRepository] 原子寫入失敗: {e}")
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return False

    def get_all_photos(self) -> List[Dict[str, Any]]:
        """安全取得所有相片紀錄"""
        with self._lock:
            data = self._load_data_unlocked()
            return data.get("photos", [])

    def get_photo_by_id(self, photo_id: str) -> Optional[Dict[str, Any]]:
        """依 ID 取得單張相片資料"""
        with self._lock:
            data = self._load_data_unlocked()
            for photo in data.get("photos", []):
                if photo.get("id") == photo_id:
                    return photo
            return None

    def upsert_photos(self, new_photos: List[Dict[str, Any]]) -> int:
        """增量更新或插入相片紀錄"""
        if not new_photos:
            return 0
        with self._lock:
            data = self._load_data_unlocked()
            photos = data.get("photos", [])
            existing_map = {p.get("id"): idx for idx, p in enumerate(photos)}

            updated_count = 0
            for np in new_photos:
                pid = np.get("id")
                if pid in existing_map:
                    idx = existing_map[pid]
                    photos[idx].update(np)
                else:
                    photos.append(np)
                    existing_map[pid] = len(photos) - 1
                updated_count += 1

            data["photos"] = photos
            if self._save_data_atomic_unlocked(data):
                return updated_count
            return 0

    def update_people_tags(self, matches_map: Dict[str, List[str]]) -> int:
        """
        批量更新 AI 人臉辨識標籤
        matches_map 結構: {"John": [path1, path2], "Sharon": [...], "郭泊彤Sophia": [...]}
        """
        if not matches_map:
            return 0
        with self._lock:
            data = self._load_data_unlocked()
            photos = data.get("photos", [])

            # 反向建立路徑與匹配標籤對照表
            path_to_tags = {}
            managed_tags = set(matches_map.keys())
            for tag, paths in matches_map.items():
                for path in paths:
                    path_to_tags.setdefault(path, set()).add(tag)

            updated_count = 0
            for photo in photos:
                path = photo.get("path", "")
                if "people" not in photo:
                    photo["people"] = []

                # 先清除舊有的受管標籤
                photo["people"] = [p for p in photo["people"] if p not in managed_tags]

                # 寫入最新的 AI 辨識標籤
                if path in path_to_tags:
                    photo["people"].extend(list(path_to_tags[path]))
                    updated_count += 1

            data["photos"] = photos
            if self._save_data_atomic_unlocked(data):
                return updated_count
            return 0

    def delete_photos_by_path(self, deleted_paths: List[str]) -> int:
        """刪除無效照片紀錄"""
        if not deleted_paths:
            return 0
        del_set = set(deleted_paths)
        with self._lock:
            data = self._load_data_unlocked()
            photos = data.get("photos", [])
            initial_count = len(photos)
            
            photos = [p for p in photos if p.get("path") not in del_set]
            data["photos"] = photos

            removed_count = initial_count - len(photos)
            if self._save_data_atomic_unlocked(data):
                return removed_count
            return 0

# 全局單例便利存取點
default_repository = PhotoRepository()
