"""Print 'sha256  relative/path' for every file under DIR, reading with O_NOATIME so hashing does not count as opening the files
(plain sha256sum or cp would, and sloth-sort's rule is about who opened what)."""
import sys
from pathlib import Path
from sloth_sort.mover import sha
root = Path(sys.argv[1])
for p in sorted(root.rglob("*")):
    if p.is_file() and not p.name.startswith(".sloth") and p.name != "sloth-plan.html":
        print(f"{sha(p)}  {p.relative_to(root)}")
