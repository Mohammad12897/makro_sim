#!/usr/bin/env python3
"""
diagnose_py_errors.py

- Rekursiv alle .py Dateien prüfen.
- Bei SyntaxError / UnicodeDecodeError / anderen Exceptions: sofort anhalten.
- Ausgabe: Dateipfad, Fehlerart, lineno, col_offset, 10 Zeilen Kontext, hex/byte dump der problematischen Zeile,
  Suche nach Marker "# User's Edge browser tabs metadata" in der Nähe.
- Optional: --continue um alle Dateien zu prüfen (statt beim ersten Fehler zu stoppen).
"""

from pathlib import Path
import sys
import argparse
import traceback
import py_compile
import ast
import codecs
import binascii

CTX_LINES = 10

def read_text_try(path):
    # Versuche UTF-8, fallback latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc), enc
        except Exception:
            continue
    raise UnicodeDecodeError("Unable to decode file with utf-8 or latin-1")

def show_context(lines, lineno, col=None, ctx=CTX_LINES):
    start = max(1, lineno - ctx)
    end = min(len(lines), lineno + ctx)
    out = []
    for i in range(start, end+1):
        prefix = "->" if i == lineno else "  "
        line = lines[i-1].rstrip("\n")
        out.append(f"{prefix} {i:5d}: {line}")
        if i == lineno and col is not None:
            # caret under column (approx)
            caret = " " * (col + 8) + "^"
            out.append(caret)
    return "\n".join(out)

def hexdump_line(s):
    # show bytes and hex for the line
    b = s.encode("utf-8", errors="backslashreplace")
    hexed = binascii.hexlify(b).decode("ascii")
    # group hex in pairs
    pairs = " ".join(hexed[i:i+2] for i in range(0, len(hexed), 2))
    # show printable representation
    printable = "".join(ch if 32 <= ord(ch) <= 126 else repr(ch) for ch in s)
    return f"BYTES (utf-8 escaped): {pairs}\nPRINTABLE: {printable}"

def diagnose_file(path, stop_on_error=True):
    print("\n" + "="*80)
    print(f"Checking: {path}")
    try:
        text, enc = read_text_try(path)
    except Exception as e:
        print(f"[ERROR] Could not read {path}: {e}")
        return False

    # quick search for the known problematic marker
    marker = "# User's Edge browser tabs metadata"
    if marker in text:
        idx = text.find(marker)
        # compute line number of marker
        lineno = text[:idx].count("\n") + 1
        print(f"[MARKER FOUND] '{marker}' at line {lineno} in {path}")
        # show a bit of context around marker
        lines = text.splitlines(True)
        print(show_context(lines, lineno, ctx=5))
        # continue to try compile (we still want syntax diagnostics)
    # Try to compile using py_compile (gives SyntaxError with lineno/offset)
    try:
        py_compile.compile(str(path), doraise=True)
        # additionally try ast.parse to catch some encoding/ast issues
        try:
            ast.parse(text)
        except Exception as e:
            raise e
        print("[OK] Compiled successfully.")
        return True
    except SyntaxError as se:
        print("[SYNTAX ERROR]")
        print(f"  File: {path}")
        print(f"  Message: {se.msg}")
        print(f"  Line: {se.lineno}  Offset: {se.offset}")
        # show context lines
        lines = text.splitlines(True)
        print("\n--- Context ---")
        print(show_context(lines, se.lineno, col=(se.offset-1 if se.offset else None)))
        print("\n--- Problematic line hex/bytes ---")
        problem_line = lines[se.lineno-1] if 1 <= se.lineno <= len(lines) else ""
        print(hexdump_line(problem_line))
        print("\n--- Full Traceback ---")
        traceback.print_exception(se, se, se.__traceback__, limit=10)
        return False
    except UnicodeDecodeError as ude:
        print("[UNICODE DECODE ERROR]")
        print(f"  File: {path}")
        print(f"  Error: {ude}")
        # show first 200 bytes hex to inspect non-printables
        raw = path.read_bytes()
        sample = raw[:512]
        print("First 512 bytes hex:")
        print(binascii.hexlify(sample).decode("ascii"))
        return False
    except Exception as e:
        print("[OTHER ERROR]")
        print(f"  File: {path}")
        print(f"  Exception: {type(e).__name__}: {e}")
        # try to show traceback
        traceback.print_exc(limit=10)
        return False

def main():
    parser = argparse.ArgumentParser(description="Diagnose Python files for syntax/encoding issues and edge dump markers.")
    parser.add_argument("--path", "-p", default=".", help="Root path to scan")
    parser.add_argument("--continue", "-c", dest="cont", action="store_true", help="Continue scanning all files (don't stop at first error)")
    args = parser.parse_args()

    root = Path(args.path)
    py_files = sorted([p for p in root.rglob("*.py") if p.is_file()])

    if not py_files:
        print("No .py files found under", root)
        return 0

    any_fail = False
    for p in py_files:
        ok = diagnose_file(p, stop_on_error=not args.cont)
        if not ok:
            any_fail = True
            if not args.cont:
                print("\nStopped at first failure. Re-run with --continue to see all files.")
                return 2
    if any_fail:
        print("\nFinished scan: some files had issues.")
        return 1
    print("\nFinished scan: all files compiled successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
