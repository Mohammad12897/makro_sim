# scan_syntax_and_fences.py

#Scans repo for:
#- unclosed markdown code fences (```),
#- unclosed Python string literals (', ", ''' or """),
#- unbalanced brackets in .py,
#- very long lines and NUL bytes,
#- known marker strings like edge_all_open_tabs (Edge browser dump).

#Stops at first finding (default) and prints detailed context and hex dump.
#Use --continue to scan all files.
# python ./scripts/scan_syntax_and_fences.py -p risk_dashboard/ui/profiles_ui.py
# python ./scripts/scan_syntax_and_fences.py -p risk_dashboard/ui/profiles_ui.py --fix
# python ./scripts/scan_syntax_and_fences.py -p risk_dashboard/ui
# python scan_syntax_and_fences.py -p risk_dashboard/ui --fix
# python ./scripts/scan_syntax_and_fences.py -p . --continue


from pathlib import Path
import argparse
import re
import binascii
import sys
import shutil
import tempfile

MAX_LINE_LEN = 2000
CTX = 10

# Robust pattern to detect the Edge browser dump block (multi-line or single-line)
EDGE_PATTERN = re.compile(r"#\s*User['’]s\s+Edge\s+browser\s+tabs\s+metadata.*?edge_all_open_tabs\s*=\s*\[.*?\]\s*",
    re.IGNORECASE | re.DOTALL
)

def hexdump_bytes(b: bytes, maxlen=512):
    sample = b[:maxlen]
    hexed = binascii.hexlify(sample).decode('ascii')
    pairs = " ".join(hexed[i:i+2] for i in range(0, len(hexed), 2))
    printable = ''.join((chr(c) if 32 <= c <= 126 else '.') for c in sample)
    return pairs, printable

def check_edge_dump(text, path):
    m = EDGE_PATTERN.search(text)
    if m:
        start = m.start()
        lineno = text[:start].count("\n") + 1
        print(f"\n[EDGE DUMP FOUND] {path} at approx line {lineno}")
        lines = text.splitlines(True)
        ctx_start = max(1, lineno-5)
        ctx_end = min(len(lines), lineno+5)
        for i in range(ctx_start, ctx_end+1):
            prefix = "->" if i==lineno else "  "
            print(f"{prefix} {i:5d}: {lines[i-1].rstrip()}")
        snippet = m.group(0)[:512].encode('utf-8', errors='replace')
        pairs, printable = hexdump_bytes(snippet)
        print("\nHex snippet of matched block (first bytes):")
        print(pairs)
        return True
    return False

def hexdump_line(s):
    b = s.encode("utf-8", errors="backslashreplace")
    hexed = binascii.hexlify(b).decode("ascii")
    pairs = " ".join(hexed[i:i+2] for i in range(0, len(hexed), 2))
    printable = "".join(ch if 32 <= ord(ch) <= 126 else '.' for ch in s)
    return pairs, printable

def find_unclosed_md_fence(lines):
    fence_open = False
    fence_line = None
    fence_re = re.compile(r"^```")
    for i, ln in enumerate(lines, start=1):
        if fence_re.match(ln):
            if not fence_open:
                fence_open = True
                fence_line = i
            else:
                fence_open = False
                fence_line = None
    if fence_open:
        return fence_line
    return None

def find_unclosed_py_strings(text):
    triple_single = text.count("'''")
    triple_double = text.count('"""')
    t_removed = text.replace("'''", "").replace('"""', "")
    single = t_removed.count("'")
    double = t_removed.count('"')
    if triple_single % 2 == 1:
        idx = text.find("'''")
        lineno = text[:idx].count("\n") + 1
        return ("triple_single", lineno)
    if triple_double % 2 == 1:
        idx = text.find('"""')
        lineno = text[:idx].count("\n") + 1
        return ("triple_double", lineno)
    if single % 2 == 1:
        idx = t_removed.find("'")
        lineno = t_removed[:idx].count("\n") + 1
        return ("single_quote", lineno)
    if double % 2 == 1:
        idx = t_removed.find('"')
        lineno = t_removed[:idx].count("\n") + 1
        return ("double_quote", lineno)
    return None


# Replace or add this function in scan_syntax_and_fences.py
import tokenize
from io import BytesIO

# Optional helper: keep original textual fallback (rename original function if present)
def check_brackets_balance_py_textual(lines):
    stack = []
    pairs = {')':'(', ']':'[', '}':'{'}
    opens = set(pairs.values())
    for i, ln in enumerate(lines, start=1):
        for ch in ln:
            if ch in opens:
                stack.append((ch, i))
            elif ch in pairs:
                if not stack or stack[-1][0] != pairs[ch]:
                    return ("unbalanced", i, ch)
                stack.pop()
    if stack:
        return ("unbalanced_open", stack[-1][1], stack[-1][0])
    return None


def check_brackets_balance_py_tokenized(text):
    """
    Tokenize-based bracket check for Python source.
    Returns None if balanced, otherwise returns a tuple like ("unbalanced", lineno, char).
    """
    pairs = {')':'(', ']':'[', '}':'{'}
    opens = set(pairs.values())
    stack = []
    try:
        tokens = tokenize.tokenize(BytesIO(text.encode('utf-8')).readline)
    except Exception:
        # If tokenization fails, fall back to text-based check to avoid hiding real errors
        return check_brackets_balance_py_textual(text.splitlines(True))
    for toknum, tokval, (srow, scol), (erow, ecol), _ in tokens:
        if toknum == tokenize.OP and tokval in opens:
            stack.append((tokval, srow, scol))
        elif toknum == tokenize.OP and tokval in pairs:
            if not stack or stack[-1][0] != pairs[tokval]:
                return ("unbalanced", srow, tokval)
            stack.pop()
    if stack:
        ch, lineno, col = stack[-1]
        return ("unbalanced_open", lineno, ch)
    return None


def check_brackets_balance_py(lines):
    stack = []
    pairs = {')':'(', ']':'[', '}':'{'}
    opens = set(pairs.values())
    for i, ln in enumerate(lines, start=1):
        for ch in ln:
            if ch in opens:
                stack.append((ch, i))
            elif ch in pairs:
                if not stack or stack[-1][0] != pairs[ch]:
                    return ("unbalanced", i, ch)
                stack.pop()
    if stack:
        return ("unbalanced_open", stack[-1][1], stack[-1][0])
    return None

def show_context(lines, lineno):
    start = max(1, lineno-CTX)
    end = min(len(lines), lineno+CTX)
    out = []
    for i in range(start, end+1):
        prefix = "->" if i==lineno else "  "
        out.append(f"{prefix} {i:5d}: {lines[i-1].rstrip()}")
    return "\n".join(out)

def remove_edge_dump_from_text(text):
    return EDGE_PATTERN.sub("", text)

def clean_file_atomic(path: Path):
    # read with encoding fallbacks
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = path.read_text(encoding=enc)
            used_enc = enc
            break
        except Exception:
            text = None
    if text is None:
        print(f"[SKIP] Cannot decode {path}")
        return False
    if not EDGE_PATTERN.search(text):
        return False
    # backup
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    new_text = remove_edge_dump_from_text(text)
    # atomic write
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    with open(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_text)
    Path(tmp).replace(path)
    print(f"[CLEANED] {path} (backup: {bak}, decoded as {used_enc})")
    return True

def inspect_file(p: Path, do_fix=False):
    try:
        raw = p.read_bytes()
    except Exception as e:
        print(f"[ERROR] Cannot read {p}: {e}")
        return False, None
    if b'\x00' in raw:
        pairs, printable = hexdump_bytes(raw, maxlen=256)
        print(f"\n[NONPRINTABLE BYTES] {p}\nFirst bytes hex: {pairs}\nPrintable: {printable}")
        return False, ("nul", 1)
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            used_enc = enc
            break
        except Exception:
            text = None
    if text is None:
        print(f"[ENCODING ERROR] {p} (could not decode with common encodings)")
        return False, ("encoding", 1)
    # Edge dump check first
    if check_edge_dump(text, p):
        if do_fix:
            cleaned = clean_file_atomic(p)
            return (not cleaned), ("edge_dump_fixed" if cleaned else "edge_dump_failed")
        return False, ("edge_dump", 1)
    lines = text.splitlines(True)
    for i, ln in enumerate(lines, start=1):
        if len(ln) > MAX_LINE_LEN:
            print(f"\n[LONG LINE] {p} line {i} length={len(ln)}")
            print(show_context(lines, i))
            pairs, printable = hexdump_bytes(ln.encode(used_enc, errors='replace'))
            print("Hex snippet:", pairs[:200])
            return False, ("longline", i)
    if p.suffix.lower() == ".md":
        fence_line = find_unclosed_md_fence(lines)
        if fence_line:
            print(f"\n[UNCLOSED MD FENCE] {p} opened at line {fence_line} (no closing ``` found)")
            print(show_context(lines, fence_line))
            return False, ("md_fence", fence_line)
    if p.suffix.lower() == ".py":
        s = find_unclosed_py_strings(text)
        if s:
            kind, lineno = s
            print(f"\n[UNCLOSED PY STRING] {p} type={kind} at approx line {lineno}")
            print(show_context(lines, lineno))
            line = lines[lineno-1] if 1 <= lineno <= len(lines) else ""
            pairs, printable = hexdump_bytes(line.encode(used_enc, errors='replace'))
            print("Line hex:", pairs)
            return False, ("py_string", lineno)
        #b = check_brackets_balance_py(lines)
        b = check_brackets_balance_py_tokenized("".join(lines))
        if b:
            print(f"\n[BRACKETS UNBALANCED] {p} info={b}")
            lineno = b[1]
            print(show_context(lines, lineno))
            return False, ("brackets", lineno)
    return True, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", "-p", default=".", help="root path or single file")
    parser.add_argument("--continue", "-c", dest="cont", action="store_true", help="scan all files")
    parser.add_argument("--fix", dest="fix", action="store_true", help="remove detected Edge dumps (creates .bak backups)")
    args = parser.parse_args()
    root = Path(args.path)
    if root.is_file():
        files = [root]
    else:
        files = sorted([p for p in root.rglob("*") if p.suffix.lower() in {'.py', '.md', '.txt'}])
    if not files:
        print("No target files found.")
        return 0
    for p in files:
        ok, info = inspect_file(p, do_fix=args.fix)
        if not ok:
            print(f"\nStopped at {p} due to issue: {info}")
            if not args.cont:
                return 2
    print("\nScan finished: no obvious fence/string/longline issues found.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
