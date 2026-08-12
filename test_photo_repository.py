#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PhotoRepository 深層模組單元測試 (test_photo_repository.py)
"""

import os
import json
import unittest
import threading
from pathlib import Path
from photo_repository import PhotoRepository

TEST_DB_PATH = "test_photos_db.json"

class TestPhotoRepository(unittest.TestCase):
    def setUp(self):
        self.repo = PhotoRepository(db_path=TEST_DB_PATH)
        # 初始化測試用 DB
        initial_data = {
            "photos": [
                {"id": "p1", "filename": "1.jpg", "path": "Photos/2024/1.jpg", "people": []},
                {"id": "p2", "filename": "2.jpg", "path": "Photos/2024/2.jpg", "people": ["John"]}
            ]
        }
        with open(self.repo.db_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False)

    def tearDown(self):
        if self.repo.db_path.exists():
            os.remove(self.repo.db_path)
        tmp_path = self.repo.db_path.with_suffix(".json.tmp")
        if tmp_path.exists():
            os.remove(tmp_path)

    def test_get_all_photos(self):
        photos = self.repo.get_all_photos()
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0]["id"], "p1")

    def test_update_people_tags(self):
        matches = {
            "John": ["Photos/2024/1.jpg"],
            "Sharon": ["Photos/2024/1.jpg", "Photos/2024/2.jpg"]
        }
        updated = self.repo.update_people_tags(matches)
        self.assertTrue(updated > 0)

        photos = self.repo.get_all_photos()
        p1 = next(p for p in photos if p["id"] == "p1")
        p2 = next(p for p in photos if p["id"] == "p2")
        self.assertIn("John", p1["people"])
        self.assertIn("Sharon", p1["people"])
        self.assertIn("Sharon", p2["people"])

    def test_concurrent_writes(self):
        """測試多執行緒併發寫入安全性"""
        threads = []
        def worker(thread_id):
            new_p = [{"id": f"c_{thread_id}", "filename": f"{thread_id}.jpg", "path": f"Photos/{thread_id}.jpg"}]
            self.repo.upsert_photos(new_p)

        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        photos = self.repo.get_all_photos()
        self.assertEqual(len(photos), 12) # 2 初始 + 10 併發寫入

if __name__ == "__main__":
    unittest.main()
