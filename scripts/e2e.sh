#!/usr/bin/env bash
# End-to-end on a throwaway FICTIONAL Downloads folder: generate -> plan (nice 19) -> report -> apply -> tree -> undo -> byte-for-byte check.
# Usage: e2e.sh WORK_DIR   (run from the repo root, with the model server up). Hashing uses O_NOATIME so it never "opens" a file.
set -euo pipefail
WORK="$1"; CONF=eval/downloads.toml; rm -rf "$WORK"; mkdir -p "$WORK"
S=.venv/bin/sloth; PY=.venv/bin/python
$PY eval/make_downloads_folder.py "$WORK/Downloads"
$PY scripts/hash_tree.py "$WORK/Downloads" > "$WORK/before.sha"
date -Is; echo "\$ sloth plan Downloads --nice 19"; time $S plan "$WORK/Downloads" --config "$CONF" --nice 19
echo "\$ sloth report"; $S report "$WORK/Downloads"
echo "\$ sloth apply"; time $S apply "$WORK/Downloads" --config "$CONF"
echo "\$ ls"; ls -R "$WORK/Downloads" | head -90
echo "\$ sloth undo"; $S undo "$WORK/Downloads"
$PY scripts/hash_tree.py "$WORK/Downloads" > "$WORK/after.sha"
if diff -q "$WORK/before.sha" "$WORK/after.sha" >/dev/null; then echo "UNDO CHECK: all $(wc -l < "$WORK/before.sha") files are back, byte for byte"; else echo "UNDO CHECK FAILED"; exit 1; fi
