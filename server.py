#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
個人相片 Web 管理伺服器 (server.py) - 高效多線程與非阻塞版
提供：
1. 多線程 HTTP Server (ThreadingHTTPServer)
2. 靜態網頁與圖片高效流式伺服
3. 非同步背景掃描 (/api/trigger_import 不會阻塞網頁載入)
"""

import os
import sys
import json
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from organize_photos import process_photos, DB_FILE, BASE_DIR

PORT = 8095

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

class PhotoHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 簡化日誌輸出
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        # API: 取得所有相片資料
        if parsed_path.path == "/api/photos":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            
            if DB_FILE.exists():
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"photos": [], "updated_at": ""}).encode("utf-8"))
            return

        # 靜態檔案預設回傳 index.html
        if parsed_path.path == "/":
            self.path = "/index.html"
            
        return super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        # API: 更新相片人物標籤
        if parsed_path.path == "/api/update_people":
            try:
                data = json.loads(body)
                photo_id = data.get("id")
                people = data.get("people", [])
                
                if DB_FILE.exists():
                    with open(DB_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                    
                    found = False
                    for photo in db_data.get("photos", []):
                        if photo["id"] == photo_id:
                            photo["people"] = people
                            found = True
                            break
                    
                    if found:
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(db_data, f, ensure_ascii=False, indent=2)
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "people": people}).encode("utf-8"))
                        return

                self.send_error(404, "Photo not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # API: 觸發掃描歸檔新照片與 AI 人臉辨識分類（非阻塞背景執行緒）
        if parsed_path.path == "/api/trigger_import":
            def run_import_in_background():
                try:
                    print("\n🚀 啟動【全套自動化相片匯入與 AI 人臉辨識流程】...")
                    
                    # 步驟 1: 增量掃描匯入新照片檔
                    print("📁 [步驟 1/3] 增量掃描與歸檔新照片...")
                    process_photos(BASE_DIR)
                    
                    # 步驟 2: 清理已刪除照片索引
                    print("🗑️ [步驟 2/3] 自動清理已手動刪除的照片索引...")
                    try:
                        from rescan_and_purge_deleted import purge_and_rescan
                        purge_and_rescan()
                    except Exception as pe:
                        print(f"⚠️ 清理已刪除相片微調提示: {pe}")

                    # 步驟 3: 啟動 InsightFace ArcFace 512維 AI 人臉辨識與分類
                    print("🤖 [步驟 3/3] 啟動 InsightFace ArcFace 512維 AI 人臉辨識與分類 (John, Sharon, 郭泊彤Sophia)...")
                    try:
                        from insightface_recognizer import run_insightface_recognition
                        run_insightface_recognition()
                    except Exception as ie:
                        print(f"❌ AI 人臉辨識執行失敗: {ie}")

                    print("🎉 【全套自動化匯入與 AI 人臉辨識分類完畢！】\n")
                except Exception as e:
                    print(f"❌ 背景掃描與辨識失敗: {e}")

            # 啟動獨立線程，不卡住 HTTP 請求
            threading.Thread(target=run_import_in_background, daemon=True).start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success", 
                "message": "後端已開始非同步重新掃描照片與 AI 人臉辨識分類！網頁可繼續順暢使用。"
            }).encode("utf-8"))
            return

        self.send_error(404, "API not found")

def run_server():
    os.chdir(BASE_DIR)
    ports_to_try = [8099, 8085, 8090, 8095, 9000]
    httpd = None
    actual_port = None

    for p in ports_to_try:
        try:
            server_address = ('', p)
            httpd = ReusableThreadingHTTPServer(server_address, PhotoHandler)
            actual_port = p
            break
        except OSError:
            continue

    if not httpd:
        sys.exit(1)

    with open(BASE_DIR / "server_port.txt", "w", encoding="utf-8") as f:
        f.write(str(actual_port))

    print(f"🚀 個人相片管理系統已成功啟動！")
    print(f"🔗 請開啟此連結: http://localhost:{actual_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 伺服器已停止。")

if __name__ == "__main__":
    run_server()
