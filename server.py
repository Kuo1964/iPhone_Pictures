#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
個人相片 Web 管理伺服器 (server.py) - 終極穩定版
特徵：
1. 完全自主掌控的 send_static_file，100% 支援中文與特殊字元圖片傳輸，徹底解決 404 與 BrokenPipeError。
2. 多線程與非阻塞架構 (ThreadingHTTPServer)。
3. API: /api/photos, /api/batch_update_people, /api/trigger_import
"""

import os
import sys
import json
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from organize_photos import process_photos, DB_FILE, BASE_DIR

PORT = 8080

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

class PhotoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 簡化日誌輸出
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def send_static_file(self, req_path):
        """完全自主研發的靜態檔案與圖片傳輸器，100% 支援中文與特殊路徑"""
        clean_path = urllib.parse.unquote(req_path).lstrip('/')
        if not clean_path:
            clean_path = "index.html"
            
        file_path = (BASE_DIR / clean_path).resolve()
        
        # 防止目錄穿越攻擊
        if not str(file_path).startswith(str(BASE_DIR)):
            self.send_error(403, "Forbidden")
            return
            
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return
            
        ext = file_path.suffix.lower()
        content_type = "application/octet-stream"
        if ext in [".html", ".htm"]:
            content_type = "text/html; charset=utf-8"
        elif ext in [".css"]:
            content_type = "text/css; charset=utf-8"
        elif ext in [".js"]:
            content_type = "application/javascript; charset=utf-8"
        elif ext in [".jpeg", ".jpg", ".JPG", ".JPEG"]:
            content_type = "image/jpeg"
        elif ext in [".png"]:
            content_type = "image/png"
        elif ext in [".json"]:
            content_type = "application/json; charset=utf-8"
            
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            try:
                self.send_error(500, str(e))
            except Exception:
                pass

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

        # 傳送靜態網頁或圖片檔案
        self.send_static_file(parsed_path.path)

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
                action = data.get("action", "add")
                
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
    ports_to_try = [8080, 8085, 8090, 8098, 9000]
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
