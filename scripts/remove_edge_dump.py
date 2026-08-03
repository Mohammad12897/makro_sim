# remove_edge_dump.py
from pathlib import Path

start_marker = "# User's Edge browser tabs metadata"

for p in Path('.').rglob('*'):
    if p.suffix in {'.py', '.md', '.txt'}:
        text = p.read_text(encoding='utf-8', errors='ignore')
        if start_marker in text:
            idx = text.find(start_marker)
            # Suche schließende ']' nach idx
            end_idx = text.find(']', idx)
            if end_idx != -1:
                new_text = text[:idx] + text[end_idx+1:]
            else:
                new_text = text[:idx]
            p.write_text(new_text, encoding='utf-8')
            print("Cleaned", p)
