#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InsightFace (ArcFace 512維) 2023年份相片專用精準辨識腳本 (insightface_recognizer_2023.py)
特色：
1. 僅對 2023 年的照片 (year == "2023") 進行人物分類，絕對不動其他年份與地點的照片。
2. 載入全新的 John、Sharon 與 Sophia (雙重多時期) 高清基準照片。
3. 標籤 100% 僅更新寫入 photos_db.json，0 個實體檔案與檔名被修改。
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

JOHN_BASE_PATH = BASE_DIR / "references/john_base.png"
SHARON_BASE_PATH = BASE_DIR / "references/sharon_base.png"
SOPHIA_BASE_PATH_NEW = BASE_DIR / "references/sophia_base.png"
SOPHIA_BASE_PATH_OLD = BASE_DIR / "Photos/2013/2013-12_未知地點/65101648-FC7D-4910-9933-CDEB1BC6185F.jpeg"

def compute_cosine_similarity(emb1, emb2):
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

def run_2023_recognition():
    print("🚀 初始化 InsightFace 512維 ArcFace 2023專用辨識引擎...")
    app = FaceAnalysis(name="buffalo_l", allowed_modules=['detection', 'recognition'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("✅ InsightFace 512維引擎加載成功！")

    # 1. 載入 John 基準
    john_embs = []
    if JOHN_BASE_PATH.exists():
        img = cv2.imread(str(JOHN_BASE_PATH))
        if img is not None:
            faces = app.get(img)
            if faces:
                john_embs.append(faces[0].embedding)
                print("  💙 成功提取 John (您本人) 高清 512維特徵向量！")

    # 2. 載入 Sharon 基準
    sharon_embs = []
    if SHARON_BASE_PATH.exists():
        img = cv2.imread(str(SHARON_BASE_PATH))
        if img is not None:
            faces = app.get(img)
            if faces:
                sharon_embs.append(faces[0].embedding)
                print("  💜 成功提取 Sharon (太太) 高清 512維特徵向量！")

    # 3. 載入 Sophia 雙重多時期基準 (長大大頭照 + 幼童照片)
    sophia_embs = []
    for p in [SOPHIA_BASE_PATH_NEW, SOPHIA_BASE_PATH_OLD]:
        if p.exists():
            img = cv2.imread(str(p))
            if img is not None:
                faces = app.get(img)
                if faces:
                    sophia_embs.append(faces[0].embedding)
    print(f"  💖 成功提取 郭泊彤Sophia (女兒) {len(sophia_embs)} 組雙重多時期 512維特徵向量！")

    # 4. 讀取 DB 並鎖定 2023 年相片
    if not DB_FILE.exists():
        print("❌ 找不到 photos_db.json！")
        return

    with open(DB_FILE, "r", encoding="utf-8") as f:
        db_data = json.load(f)

    photos_2023 = [p for p in db_data.get("photos", []) if p.get("year") == "2023"]
    print(f"\n📁 專向鎖定 2023 年相片總計 {len(photos_2023)} 張，開始進行 AI 人臉辨識...")

    matched_john = 0
    matched_sharon = 0
    matched_sophia = 0
    scanned = 0
    t0 = time.time()

    for photo in photos_2023:
        scanned += 1
        rel_path = photo.get("path")
        if not rel_path:
            continue
            
        full_path = BASE_DIR / rel_path
        if not full_path.exists():
            continue

        img = cv2.imread(str(full_path))
        if img is None:
            continue

        faces = app.get(img)
        if not faces:
            continue

        if "people" not in photo:
            photo["people"] = []

        # 僅清空 2023 照片中的舊標籤
        photo["people"] = [p for p in photo["people"] if p not in ["John", "Sharon", "郭泊彤Sophia"]]

        for face in faces:
            emb = face.embedding

            # John 比對 (> 0.40)
            if john_embs:
                for j_emb in john_embs:
                    sim = compute_cosine_similarity(emb, j_emb)
                    if sim > 0.40:
                        if "John" not in photo["people"]:
                            photo["people"].append("John")
                            matched_john += 1
                            print(f"  💙 [2023 John 匹配] {photo['filename']} (相似度: {sim:.3f})")
                        break

            # Sharon 比對 (> 0.40)
            if sharon_embs:
                for s_emb in sharon_embs:
                    sim = compute_cosine_similarity(emb, s_emb)
                    if sim > 0.40:
                        if "Sharon" not in photo["people"]:
                            photo["people"].append("Sharon")
                            matched_sharon += 1
                            print(f"  💜 [2023 Sharon 匹配] {photo['filename']} (相似度: {sim:.3f})")
                        break

            # Sophia 雙重比對 (> 0.40)
            if sophia_embs:
                for s_emb in sophia_embs:
                    sim = compute_cosine_similarity(emb, s_emb)
                    if sim > 0.40:
                        if "郭泊彤Sophia" not in photo["people"]:
                            photo["people"].append("郭泊彤Sophia")
                            matched_sophia += 1
                            print(f"  💖 [2023 Sophia 匹配] {photo['filename']} (相似度: {sim:.3f})")
                        break

        if scanned % 100 == 0:
            print(f"⏳ 已完成 2023 相片辨識 {scanned} / {len(photos_2023)} 張 ({time.time() - t0:.1f} 秒)...")

    # 5. 更新寫回 photos_db.json
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 2023 年相片人物辨識分類完全成功！耗時 {time.time() - t0:.1f} 秒")
    print(f"  ├─ 💙 2023 John (您本人) 相片: {matched_john} 張")
    print(f"  ├─ 💜 2023 Sharon (太太) 相片: {matched_sharon} 張")
    print(f"  └─ 💖 2023 郭泊彤Sophia (女兒) 相片: {matched_sophia} 張")
    print(f"  🔒 其他年份相片 100% 完全未改動，0 個實體檔案與檔名被修改。")

if __name__ == "__main__":
    run_2023_recognition()
