#!/usr/bin/env python3
# coding: utf-8
"""
Unquarantine presets: move files from presets/quarantine/ back to presets/
and append audit entries to reports/audit.jsonl.
"""
from __future__ import annotations
import os
import shutil
import json
from datetime import datetime, timezone

QDIR = "presets/quarantine"
PDIR = "presets"
AUDIT = "reports/audit.jsonl"

os.makedirs(PDIR, exist_ok=True)
os.makedirs(os.path.dirname(AUDIT) or ".", exist_ok=True)

moved = []
if not os.path.isdir(QDIR):
    print("No quarantine directory found:", QDIR)
else:
    for fname in sorted(os.listdir(QDIR)):
        if not fname.startswith("preset_") or not fname.endswith(".json"):
            continue
        src = os.path.join(QDIR, fname)
        dst = os.path.join(PDIR, fname)
        try:
            shutil.move(src, dst)
            moved.append(dst)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "unquarantine_preset",
                "file": dst
            }
            with open(AUDIT, "a", encoding="utf-8") as af:
                af.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print("Failed to move", src, "->", dst, ":", e)

print("Moved back:", moved)
