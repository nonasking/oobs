#!/usr/bin/env bash
# oobs 설치 — venv + CLI 링크 + 슬래시 커맨드 심볼릭 링크 + 설정 파일.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say() { printf "  %s\n" "$*"; }

printf "oobs CLI 설치\n"
if [[ ! -d "$REPO_ROOT/.venv" ]]; then
  python3 -m venv "$REPO_ROOT/.venv"
  say "venv 생성"
fi
"$REPO_ROOT/.venv/bin/pip" install -q -e "$REPO_ROOT"
mkdir -p "$HOME/.local/bin"
ln -sfn "$REPO_ROOT/.venv/bin/oobs" "$HOME/.local/bin/oobs"
say "CLI 링크: ~/.local/bin/oobs"

printf "\n설정 파일\n"
CONFIG="$HOME/.config/oobs/config.yaml"
if [[ ! -f "$CONFIG" ]]; then
  mkdir -p "$(dirname "$CONFIG")"
  cp "$REPO_ROOT/config.example.yaml" "$CONFIG"
  say "생성: $CONFIG"
else
  say "이미 있음: $CONFIG"
fi

printf "\n볼트 대시보드 (Obsidian Bases)\n"
VAULT="$("$REPO_ROOT/.venv/bin/python" -c "from oobs import config; print(config.load()['vault'])" 2>/dev/null)"
if [[ -n "$VAULT" ]]; then
  mkdir -p "$VAULT"
  if [[ ! -f "$VAULT/작업보드.base" ]]; then
    cp "$REPO_ROOT/templates/작업보드.base" "$VAULT/작업보드.base"
    say "생성: $VAULT/작업보드.base"
  else
    say "이미 있음: $VAULT/작업보드.base"
  fi
fi

printf "\n슬래시 커맨드 등록\n"
TARGET_DIR="$HOME/.claude/commands"
mkdir -p "$TARGET_DIR"
for name in oobs.md oobs-note.md oobs-tower.md; do
  ln -sfn "$REPO_ROOT/commands/$name" "$TARGET_DIR/$name"
  say "링크: $TARGET_DIR/$name"
done

printf "\n사용법:\n"
say "셸 직접 (Claude 우회 — 가장 안전):"
say "  oobs new --title \"...\" --status \"진행 중\" --due 2026-06-30"
say "  oobs note \"<검색어>\" \"<메모>\" [--status \"배포 대기\"]"
say "  oobs done \"<검색어>\" [\"<메모>\"] [--cancel]"
say "  oobs list [--all | --status \"진행 중\"]"
say "  oobs inbox 갑자기 생각난 메모"
say "슬래시: /oobs (세션 맥락 자동 요약), /oobs-note (진행 기록)"
say "노션 미러 끄기: ~/.config/oobs/config.yaml 의 mirror: false"
