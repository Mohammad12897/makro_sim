# find_edge_dump.py
import os, sys
patterns = ["edge_all_open_tabs", "User's Edge browser tabs metadata"]
roots = [ os.path.join(sys.prefix, "Lib", "site-packages"), os.getcwd() ]
for root in roots:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                for p in patterns:
                    if p in txt:
                        print(path)
                        break
            except Exception:
                continue

