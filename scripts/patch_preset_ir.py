#!/usr/bin/env python3
# coding: utf-8
"""
Patch preset_IR.json: mark stale indicators with notes and stale:true.
"""
from __future__ import annotations
import os
import json
import shutil
from datetime import datetime, timezone

PRESET = "presets/preset_IR.json"
TMP_DIR = "presets/tmp"
AUDIT = "reports/audit.jsonl"

if not os.path.exists(PRESET):
    raise SystemExit(f"Preset not found: {PRESET}")

with open(PRESET, "r", encoding="utf-8") as f:
    data = json.load(f)

snap = data.get("indicator_snapshot", {})

# Indicators to mark (from your report)
to_mark = ["FI_RES_TOTL_MO", "GC_XPN_TOTL_GD_ZS"]

changed = []
for key in to_mark:
    if key in snap:
        item = snap[key]
        notes = item.get("notes") or item.get("note") or ""
        add = "Marked stale by automated patch: value/year appear outdated; please review source."
        if notes:
            notes = notes + " | " + add
        else:
            notes = add
        item["notes"] = notes
        item["stale"] = True
        snap[key] = item
        changed.append(key)

# atomic write
os.makedirs(TMP_DIR, exist_ok=True)
tmp_path = os.path.join(TMP_DIR, os.path.basename(PRESET))
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
shutil.move(tmp_path, PRESET)

# audit
os.makedirs(os.path.dirname(AUDIT) or ".", exist_ok=True)
entry = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "action": "patch_preset",
    "file": PRESET,
    "changed_indicators": changed,
    "reason": "mark_stale_and_add_notes"
}
with open(AUDIT, "a", encoding="utf-8") as af:
    af.write(json.dumps(entry, ensure_ascii=False) + "\n")

print("Patched indicators:", changed)
