#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ImportPipeline 工作流深層模組單元測試 (test_import_pipeline.py)
"""

import time
import unittest
from import_pipeline import ImportPipeline

class TestImportPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = ImportPipeline()

    def test_initial_status(self):
        status = self.pipeline.get_status()
        self.assertEqual(status["state"], "idle")
        self.assertEqual(status["stage"], "none")
        self.assertIsNone(status["error"])

    def test_async_lock_prevention(self):
        # 手動模擬 running 狀態
        self.pipeline._update_status("running", "stage_1_organizing", "測試中")
        
        # 再次呼叫 start_import_async 應傳回 False (成功阻擋重複執行)
        res = self.pipeline.start_import_async()
        self.assertFalse(res)

if __name__ == "__main__":
    unittest.main()
