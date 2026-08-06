#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InsightFace (ArcFace 512維深度特徵) 全家三人極致精準人臉辨識引擎 (insightface_recognizer.py)
特色：
1. 採用 LFW 99.86% 世界冠軍級 ArcFace 骨幹網絡 (buffalo_l)。
2. 512 維高維特徵向量，專治年齡跨度大、角度側臉、妝容/髮型變化。
3. 載入 John、Sharon 與 Sophia 最新高清正面特寫基準檔案。
4. 100% 唯讀保護實體相片，0 個檔名與檔案內容被修改。
"""

import os
import sys
import json
import time
import cv2
import numpy as np
from pathlib import Path
import insightface
from insightface.app import FaceAnalysis

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "Photos"
DB_FILE = BASE_DIR / "photos_db.json"

# 全家三人頂級高清特寫基準照片檔
JOHN_BASE_PNG = BASE_DIR / "references/john_base.png"
JOHN_BASE_JPG = BASE_DIR / "references/john_base.jpg"

SHARON_BASE_PNG = BASE_DIR / "references/sharon_base.png"

SOPHIA_BASE_NEW = BASE_DIR / "references/sophia_base.png"
SOPHIA_BASE_OLD = BASE_DIR / "Photos/2013/2013-12_未知地點/65101648-FC7D-4910-9933-CDEB1BC6185F.jpeg"

def compute_cosine_similarity(emb1, emb2):
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

def run_insightface_recognition():
    print("🚀 初始化 InsightFace 512維 ArcFace 深度人臉分析引擎 (buffalo_l)...")
    app = FaceAnalysis(name="buffalo_l", allowed_modules=['detection', 'recognition'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("✅ InsightFace 深度引擎加載成功！")

    # 1. 提取 John (您本人) 基準向量 (.png 與 .jpg 雙重兼容)
    john_embs = []
    for p in [JOHN_BASE_PNG, JOHN_BASE_JPG]:
        if p.exists():
            img = cv2.imread(str(p))
            if img is not None:
                faces = app.get(img)
                if faces:
                    john_embs.append(faces[0].embedding)
                    print(f"  💙 成功提取 John (您本人) 高清 512維特徵向量: {p.name}")
                    break

    # 2. 提取 Sharon (太太) 基準向量
    sharon_embs = []
    if SHARON_BASE_PNG.exists():
        img = cv2.imread(str(SHARON_BASE_PNG))
        if img is not None:
            faces = app.get(img)
            if faces:
                sharon_embs.append(faces[0].embedding)
                print("  💜 成功提取 Sharon (太太) 高清 512維特徵向量！")

    # 3. 提取 郭泊彤Sophia (女兒) 雙重多時期基準向量 (長大大頭照 + 幼童照)
    sophia_embs = []
    for p in [SOPHIA_BASE_NEW, SOPHIA_BASE_OLD]:
        if p.exists():
            img = cv2.imread(str(p))
            if img is not None:
                faces = app.get(img)
                if faces:
                    sophia_embs.append(faces[0].embedding)
    print(f"  💖 成功提取 郭泊彤Sophia (女兒) {len(sophia_embs)} 組雙重多時期 512維特徵向量！")

    if not john_embs and not sharon_embs and not sophia_embs:
        print("❌ 無法獲取任何基準照片人臉向量！")
        return

    # 4. 全庫照片深度比對
    print("\n📸 開始使用 ArcFace 512維向量全庫辨識 John、Sharon 與 郭泊彤Sophia...")
    valid_exts = {".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG"}
    photo_files = [f for f in PHOTOS_DIR.rglob("*") if f.is_file() and f.suffix in valid_exts]
    
    print(f"📁 收集到 {len(photo_files)} 張相片，啟動 ArcFace 核心矩陣計算...")

    john_matches = set()
    sharon_matches = set()
    sophia_matches = set()
    scanned = 0
    t0 = time.time()

    for photo_path in photo_files:
        scanned += 1
        rel_path = str(photo_path.relative_to(BASE_DIR))
        
        img = cv2.imread(str(photo_path))
        if img is None:
            continue
            
        faces = app.get(img)
        if not faces:
            continue

        for face in faces:
            emb = face.embedding

            # John 比對 (Cos Similarity > 0.40)
            if john_embs:
                for j_emb in john_embs:
                    sim = compute_cosine_similarity(emb, j_emb)
                    if sim > 0.40:
                        john_matches.add(rel_path)
                        print(f"  💙 [John 匹配] {photo_path.name} (相似度: {sim:.3f})")
                        break

            # Sharon 比對 (Cos Similarity > 0.40)
            if sharon_embs:
                for s_emb in sharon_embs:
                    sim = compute_cosine_similarity(emb, s_emb)
                    if sim > 0.40:
                        sharon_matches.add(rel_path)
                        print(f"  💜 [Sharon 匹配] {photo_path.name} (相似度: {sim:.3f})")
                        break

            # 郭泊彤Sophia 雙重比對 (Cos Similarity > 0.40)
            if sophia_embs:
                for s_emb in sophia_embs:
                    sim = compute_cosine_similarity(emb, s_emb)
                    if sim > 0.40:
                        sophia_matches.add(rel_path)
                        print(f"  💖 [Sophia 匹配] {photo_path.name} (相似度: {sim:.3f})")
                        break

        if scanned % 500 == 0:
            print(f"⏳ 已深度辨識 {scanned} / {len(photo_files)} 張相片 ({time.time() - t0:.1f} 秒)...")

    print(f"\n🎉 ArcFace 512維極致辨識完畢！耗時 {time.time() - t0:.1f} 秒")
    print(f"  ├─ 💙 John (您本人) 確鑿照片: {len(john_matches)} 張")
    print(f"  ├─ 💜 Sharon (太太) 確鑿照片: {len(sharon_matches)} 張")
    print(f"  └─ 💖 郭泊彤Sophia (女兒) 確鑿照片: {len(sophia_matches)} 張")

    # 5. 更新寫入 photos_db.json
    if DB_FILE.exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db_data = json.load(f)

        updated_count = 0
        for photo in db_data.get("photos", []):
            path = photo.get("path", "")
            if "people" not in photo:
                photo["people"] = []
                
            # 重設舊標籤
            photo["people"] = [p for p in photo["people"] if p not in ["John", "Sharon", "郭泊彤Sophia"]]

            if path in john_matches:
                photo["people"].append("John")
                updated_count += 1
            if path in sharon_matches:
                photo["people"].append("Sharon")
                updated_count += 1
            if path in sophia_matches:
                photo["people"].append("郭泊彤Sophia")
                updated_count += 1

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)

        print(f"💾 標籤資料庫 photos_db.json 已成功全量同步！(0 個檔案與檔名被修改)")

if __name__ == "__main__":
    run_insightface_recognition()
