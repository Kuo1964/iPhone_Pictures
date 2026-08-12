#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InsightFace 相向相容入口腳本 (insightface_recognizer.py)
自動導向至通用精準人臉辨識模組 face_recognizer.py
"""

import sys
from face_recognizer import run_face_recognition

if __name__ == "__main__":
    target_year = sys.argv[1] if len(sys.argv) > 1 else None
    run_face_recognition(target_year)
