#check_brackets_tokenized.py
#python ./scripts/check_brackets_tokenized.py path/to/file.py

from pathlib import Path
import sys
import tokenize
from io import BytesIO

pairs = {')': '(', ']': '[', '}': '{'}
opens = set(pairs.values())

def check(path):
    stack = []
    data = Path(path).read_bytes()
    try:
        tokens = tokenize.tokenize(BytesIO(data).readline)
    except Exception as e:
        print("Tokenize error:", e)
        return False
    for toknum, tokval, (srow, scol), (erow, ecol), _ in tokens:
        # Only consider operator tokens for bracket matching
        if toknum == tokenize.OP and tokval in opens:
            stack.append((tokval, srow, scol))
        elif toknum == tokenize.OP and tokval in pairs:
            if not stack or stack[-1][0] != pairs[tokval]:
                print(f"UNMATCHED CLOSING {tokval!r} at {path}:{srow}:{scol}")
                return False
            stack.pop()
    if stack:
        print("UNMATCHED OPENING(s):")
        for ch, lineno, col in stack:
            print(f"  {ch!r} opened at {path}:{lineno}:{col}")
        return False
    print("All brackets balanced in", path)
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_brackets_tokenized.py path/to/file.py")
        sys.exit(2)
    ok = check(sys.argv[1])
    sys.exit(0 if ok else 1)
