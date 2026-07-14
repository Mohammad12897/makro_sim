# scripts/cleanup_edge_metadata.py
# python scripts/cleanup_edge_metadata.py
import os
import re
import shutil

ROOT = r"C:\Projects\makro_sim"   # anpassen falls nötig

# Muster so schreiben, dass sie auch über mehrere Zeilen matchen
PATTERNS = [r"#\s*
