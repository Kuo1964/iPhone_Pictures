#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
iPhone_Pictures 工作流編排深層模組 (import_pipeline.py)
特色：
1. 封裝一條龍多階段處理 (照片無損歸檔 ➔ 無效照片清理 ➔ AI 人臉辨識)。
2. 提供即時任務狀態追蹤 (idle, running, stage_1_organizing, stage_2_purging, stage_3_recognizing, completed, failed)。
3. 內建 threading.Lock() 防護，防止使用者連續點擊「重新掃描/匯入」產生競態衝突。
4. 全階段完善 Exception 捕獲與日誌保存，徹底消除 Swallow Exception 氣味。
5. 100% 唯讀保護實體相片檔案。
"""

import os
import sys
import time
import threading
from typing import Dict, Any

class ImportPipeline:
    def __init__(self):
        self._lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._status = {
            "state": "idle",
            "stage": "none",
            "message": "系統就緒",
            "start_time": None,
            "end_time": None,
            "elapsed_seconds": 0,
            "error": None
        }

    def _update_status(self, state: str, stage: str, message: str, error: str = None):
        with self._status_lock:
            self._status["state"] = state
            self._status["stage"] = stage
            self._status["message"] = message
            self._status["error"] = error
            if state == "running" and self._status["start_time"] is None:
                self._status["start_time"] = time.time()
                self._status["end_time"] = None
            elif state in ["completed", "failed"]:
                self._status["end_time"] = time.time()
                if self._status["start_time"]:
                    self._status["elapsed_seconds"] = round(self._status["end_time"] - self._status["start_time"], 1)

    def get_status(self) -> Dict[str, Any]:
        """傳回當前工作流狀態紀錄"""
        with self._status_lock:
            status_copy = dict(self._status)
            if status_copy["state"] == "running" and status_copy["start_time"]:
                status_copy["elapsed_seconds"] = round(time.time() - status_copy["start_time"], 1)
            return status_copy

    def run_import_sync(self) -> Dict[str, Any]:
        """同步執行一條龍工作流 (包含歸檔、清理、AI 辨識)"""
        # 防止併發多條管線同時執行
        if not self._lock.acquire(blocking=False):
            print("⚠️ [ImportPipeline] 已有另一個匯入工作流在執行中，忽略本次觸發。")
            return self.get_status()

        try:
            self._status["start_time"] = None  # 重置計時
            self._update_status("running", "stage_1_organizing", "階段 1/3: 正在掃描並無損歸檔新照片...")
            print("🚀 [ImportPipeline 階段 1/3] 開始無損相片整理...")
            
            # 階段 1: 無損相片整理
            from organize_photos import process_photos
            process_photos()

            # 階段 2: 重新掃描全庫並清理已刪除照片
            self._update_status("running", "stage_2_purging", "階段 2/3: 正在重新掃描全庫並清理已刪除照片...")
            print("🚀 [ImportPipeline 階段 2/3] 開始清理已刪除相片...")
            from rescan_and_purge_deleted import purge_and_rescan
            purge_and_rescan()

            # 階段 3: InsightFace ArcFace 512維 AI 人臉辨識
            self._update_status("running", "stage_3_recognizing", "階段 3/3: 正在執行 AI 人臉辨識與分類 (John, Sharon, 郭泊彤Sophia)...")
            print("🚀 [ImportPipeline 階段 3/3] 開始 InsightFace AI 人臉辨識...")
            from face_recognizer import run_face_recognition
            run_face_recognition()

            self._update_status("completed", "finished", "一條龍匯入與 AI 辨識全量完成！")
            print("✅ [ImportPipeline] 一條龍工作流順利完成！")

        except Exception as e:
            err_msg = f"工作流執行失敗: {str(e)}"
            print(f"❌ [ImportPipeline] {err_msg}")
            self._update_status("failed", "error", err_msg, error=str(e))
        finally:
            self._lock.release()

        return self.get_status()

    def start_import_async(self) -> bool:
        """非同步啟動一條龍工作流 (開背景 Thread)"""
        with self._status_lock:
            if self._status["state"] == "running":
                print("⚠️ [ImportPipeline] 工作流正在運行中，請勿重複觸發。")
                return False

        thread = threading.Thread(target=self.run_import_sync, daemon=True)
        thread.start()
        return True

# 全局單例便利存取點
default_pipeline = ImportPipeline()
