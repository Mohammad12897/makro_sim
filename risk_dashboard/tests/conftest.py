# tests/conftest.py
import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_root = os.path.abspath(os.path.join(repo_root, "src", "makro-sim"))

for p in (repo_root, src_root):
    if p not in sys.path:
        sys.path.insert(0, p)
