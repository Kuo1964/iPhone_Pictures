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

PORT = 8080

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

class PhotoHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 簡化日誌輸出
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def do_GET(self):
        # 對 URL 進行中文 unquote 解碼，確保 macOS 檔案系統正確存取
        self.path = urllib.parse.unquote(self.path)
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
        
        # API: 批量更新相片人物標籤
        if parsed_path.path == "/api/batch_update_people":
            try:
                data = json.loads(body)
                photo_ids = data.get("photo_ids", [])
                person = data.get("person", "")
                action = data.get("action", "add") # 'add' or 'remove'
                
                if photo_ids and person and DB_FILE.exists():
                    with open(DB_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                    
                    updated_count = 0
                    for photo in db_data.get("photos", []):
                        if photo["id"] in photo_ids:
                            if "people" not in photo:
                                photo["people"] = []
                            if action == "add" and person not in photo["people"]:
                                photo["people"].append(person)
                                updated_count += 1
                            elif action == "remove" and person in photo["people"]:
                                photo["people"].remove(person)
                                updated_count += 1

                    with open(DB_FILE, "w", encoding="utf-8") as f:
                        json.dump(db_data, f, ensure_ascii=False, indent=2)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success", 
                        "message": f"成功為 {updated_count} 張相片標記 [{person}]！",
                        "updated_count": updated_count
                    }).encode("utf-8"))
                    return

                self.send_error(400, "Invalid params")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # API: 觸發掃描歸檔新照片（非阻塞背景執行緒）
        if parsed_path.path == "/api/trigger_import":
            def run_import_in_background():
                try:
                    print("🔄 背景非同步開始重新掃描歸檔...")
                    process_photos(BASE_DIR)
                    print("✅ 背景非同步掃描歸檔完成！")
                except Exception as e:
                    print(f"❌ 背景掃描失敗: {e}")

            # 啟動獨立線程，不卡住 HTTP 請求
            threading.Thread(target=run_import_in_background, daemon=True).start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success", 
                "message": "後端已開始非同步重新掃描與歸檔照片！網頁可繼續順暢使用。"
            }).encode("utf-8"))
            return

        self.send_error(404, "API not found")

def run_server():
    os.chdir(BASE_DIR)
    ports_to_try = [8080, 8085, 8090, 8098, 8888, 9000]
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
        print("❌ 嘗試所有預設連接埠皆失敗。")
        sys.exit(1)

    # 記錄目前運行的 PORT
    with open(BASE_DIR / "server_port.txt", "w", encoding="utf-8") as f:
        f.write(str(actual_port))

    print(f"🚀 個人相片管理系統已成功啟動！")
    print(f"🔗 請點擊開啟此連結: http://localhost:{actual_port}")
    print(f"按 Ctrl+C 可停止伺服器。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 伺服器已停止。")

if __name__ == "__main__":
    run_server()
