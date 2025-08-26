#!/usr/bin/env bash
set -e

if ! command -v pkg >/dev/null 2>&1; then
  echo "Error: pkg command not found. Run this script inside Termux." >&2
  exit 1
fi

pkg update -y && pkg upgrade -y
pkg install -y git python nodejs

REPO_DIR="$HOME/Awesome-Telegram-OSINT"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull --ff-only
else
  git clone https://github.com/ItIsMeCall911/Awesome-Telegram-OSINT.git "$REPO_DIR"
fi

echo "Repository ready at $REPO_DIR"
echo "View the list with: less \"$REPO_DIR/README.md\""
