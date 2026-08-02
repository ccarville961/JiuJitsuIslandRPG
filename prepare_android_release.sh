#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RELEASE_DIR="$PROJECT_ROOT/android-release"

echo "Preparing clean Android runtime package..."
echo "Source:  $PROJECT_ROOT"
echo "Target:  $RELEASE_DIR"

rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

rsync -a \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.buildozer/' \
  --exclude='.venv/' \
  --exclude='JiuJitsuIslandRPG-venv/' \
  --exclude='JJI-android-venv/' \
  --exclude='android-release/' \
  --exclude='bin/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='docs/' \
  --exclude='tests/' \
  --exclude='scripts/' \
  --exclude='release-macos/' \
  --exclude='release-windows/' \
  --exclude='__pycache__/' \
  --exclude='.gitignore' \
  --exclude='.gitattributes' \
  --exclude='.DS_Store' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.bak' \
  --exclude='*.backup' \
  --exclude='*.log' \
  --exclude='*.spec' \
  --exclude='*.md' \
  --exclude='*.txt' \
  --exclude='tox.ini' \
  --exclude='Makefile' \
  --exclude='MANIFEST.in' \
  --exclude='pyproject.toml' \
  --exclude='requirements.txt' \
  --exclude='buildozer.spec' \
  --exclude='prepare_android_release.sh' \
  --exclude='*_backup_*' \
  --exclude='*-backup' \
  --exclude='audit_*.py' \
  --exclude='extract_*.py' \
  --exclude='install_*.py' \
  --exclude='fix_*.py' \
  "$PROJECT_ROOT/" "$RELEASE_DIR/"

echo
echo "Android runtime package created."
echo "Files: $(find "$RELEASE_DIR" -type f | wc -l | tr -d ' ')"
echo "Size:  $(du -sh "$RELEASE_DIR" | awk '{print $1}')"
