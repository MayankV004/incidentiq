#!/usr/bin/env bash
set -euo pipefail

# Hot SQLite backup and restore utility using Python's sqlite3 online backup API.
# Usage:
#   ./scripts/backup_sqlite.sh [src_db] [dest_backup]
#   ./scripts/backup_sqlite.sh --restore <backup_file> <target_db>

if [[ "${1:-}" == "--restore" ]]; then
  SRC="${2:?Usage: $0 --restore <backup_file> <target_db>}"
  DST="${3:?Usage: $0 --restore <backup_file> <target_db>}"
else
  SRC="${1:-${SQLITE_DB_PATH:-/data/incidentiq.db}}"
  mkdir -p backups
  DST="${2:-backups/incidentiq_$(date -u +%Y%m%dT%H%M%SZ).db}"
fi

python3 - "$SRC" "$DST" <<'PY'
import os
import sqlite3
import sys

src_path, dst_path = sys.argv[1], sys.argv[2]
if not os.path.exists(src_path):
    print(f"Source database does not exist: {src_path}", file=sys.stderr)
    sys.exit(1)

os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
src = sqlite3.connect(src_path)
dst = sqlite3.connect(dst_path)
try:
    src.backup(dst)
    dst.commit()
finally:
    dst.close()
    src.close()
print(f"SQLite backup copied cleanly: {src_path} -> {dst_path}")
PY
