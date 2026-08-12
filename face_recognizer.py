#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InsightFace (ArcFace 512維深度特徵) 全家三人通用精準人臉辨識引擎 (face_recognizer.py)
特色：
1. 支援通用辨識與專向年份辨識: run_face_recognition(target_year=None)。
2. 集中管理人物配置 (John, Sharon, 郭泊彤Sophia) 與全家三大高清基準大頭照。
3. 導入 PhotoRepository 深層模組進行原子更新與併發防禦。
4. 100% 唯讀保護實體相片，0 個檔名、二進位內容與資料夾名稱被修改。
"""

import os
import sys
import time
import cv2
import numpy as np
from pathlib import Path
import insightface
from insightface.app import FaceAnalysis
from photo_repository import default_repository

BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# 🎯 全家三人頂級 AI 基準照片配置與相似度門檻
# ==========================================
SIMILARITY_THRESHOLD = 0.40

BASE_CONFIGS = [
    {
        "name": "John",
        "label": "John",
        "icon": "💙",
        "paths": [
            BASE_DIR / "references/john_base.png",
            BASE_DIR / "references/john_base.jpg"
        ]
    },
    {
        "name": "Sharon",
        "label": "Sharon",
        "icon": "💜",
        "paths": [
            BASE_DIR / "references/sharon_base.png"
        ]
    },
    {
        "name": "Sophia",
        "label": "郭泊彤Sophia",
        "icon": "💖",
        "paths": [
            BASE_DIR / "references/sophia_base.png",
            BASE_DIR / "Photos/2013/2013-12_未知地點/65101648-FC7D-4910-9933-CDEB1BC6185F.jpeg"
        ]
    }
]

def compute_cosine_similarity(emb1, emb2):
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

def run_face_recognition(target_year=None):
    mode_desc = f"【專向年份 {target_year}】" if target_year else "【全庫照片】"
    print(f"🚀 啟動 InsightFace ArcFace 512維 AI 人臉辨識引擎 {mode_desc}...")
    
    app = FaceAnalysis(name="buffalo_l", allowed_modules=['detection', 'recognition'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("✅ ArcFace 512維神經網絡引擎加載成功！")

    # 1. 提取所有基準人臉的 512維 特徵向量
    person_embeddings = {}
    for config in BASE_CONFIGS:
        person_name = config["label"]
        person_embeddings[person_name] = []
        for path in config["paths"]:
            if path.exists():
                img = cv2.imread(str(path))
                if img is not None:
                    faces = app.get(img)
                    if faces:
                        person_embeddings[person_name].append(faces[0].embedding)
        print(f"  {config['icon']} 成功提取 [{person_name}] {len(person_embeddings[person_name])} 組 512維特徵向量！")

    # 2. 經由 PhotoRepository 讀取 DB
    all_photos = default_repository.get_all_photos()
    if target_year:
        target_photos = [p for p in all_photos if p.get("year") == str(target_year)]
    else:
        target_photos = all_photos

    print(f"\n📁 鎖定辨識相片總計 {len(target_photos)} 張 (目標年份: {target_year or '全部'})，開始 AI 計算...")

    # matches_map 結構: {"John": [path1, path2], "Sharon": [...], ...}
    matches_map = {config["label"]: [] for config in BASE_CONFIGS}
    scanned = 0
    t0 = time.time()

    for photo in target_photos:
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

        for face in faces:
            emb = face.embedding
            for config in BASE_CONFIGS:
                person_label = config["label"]
                icon = config["icon"]
                embs = person_embeddings.get(person_label, [])
                for ref_emb in embs:
                    sim = compute_cosine_similarity(emb, ref_emb)
                    if sim > SIMILARITY_THRESHOLD:
                        if rel_path not in matches_map[person_label]:
                            matches_map[person_label].append(rel_path)
                            print(f"  {icon} [{person_label} 匹配] {photo['filename']} (相似度: {sim:.3f})")
                        break

        if scanned % 500 == 0:
            print(f"⏳ 已完成相片辨識 {scanned} / {len(target_photos)} 張 ({time.time() - t0:.1f} 秒)...")

    # 3. 經由 PhotoRepository 原子寫入同步人臉標籤
    updated = default_repository.update_people_tags(matches_map)

    print(f"\n🎉 AI 人臉辨識分類完全成功！耗時 {time.time() - t0:.1f} 秒")
    for config in BASE_CONFIGS:
        person_label = config["label"]
        icon = config["icon"]
        count = len(matches_map[person_label])
        print(f"  ├─ {icon} {person_label} 確鑿相片: {count} 張")
    print(f"💾 已由 PhotoRepository 完成原子性寫入同步 ({updated} 張相片更新)。")
    print("  🔒 100% 保留實體檔案與檔名，0 個檔案內容被修改。")

if __name__ == "__main__":
    target_y = sys.argv[1] if len(sys.argv) > 1 else None
    run_face_recognition(target_y)
