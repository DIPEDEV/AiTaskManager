#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/.opencode/skills/task-workflow/SKILL.md"

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)       echo "unknown" ;;
    esac
}

OS=$(detect_os)

# ── opencode global paths ──────────────────────────────────────────────
case "$OS" in
    linux|macos)
        OPENCODE_GLOBAL="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/task-workflow"
        ;;
    windows)
        OPENCODE_GLOBAL="$APPDATA/opencode/skills/task-workflow"
        ;;
    *)
        OPENCODE_GLOBAL="$HOME/.config/opencode/skills/task-workflow"
        ;;
esac

# ── Claude Code global paths ───────────────────────────────────────────
case "$OS" in
    linux|macos)
        CLAUDE_GLOBAL="$HOME/.claude/skills/task-workflow"
        ;;
    windows)
        CLAUDE_GLOBAL="$HOME/.claude/skills/task-workflow"
        ;;
    *)
        CLAUDE_GLOBAL="$HOME/.claude/skills/task-workflow"
        ;;
esac

# ── Banner ─────────────────────────────────────────────────────────────
echo -e "${BOLD}task-workflow skill installer${RESET}"
echo ""
echo -e "This installs the ${CYAN}task-workflow${RESET} skill so that AI agents"
echo -e "(opencode / Claude Code) automatically know how to use the ${CYAN}task${RESET} CLI."
echo ""

# ── Check source exists ────────────────────────────────────────────────
if [ ! -f "$SKILL_SRC" ]; then
    echo -e "${RED}Error: SKILL.md not found at $SKILL_SRC${RESET}"
    exit 1
fi

# ── Ask which tools ────────────────────────────────────────────────────
echo -e "${BOLD}Where do you want to install the skill?${RESET}"
echo ""
echo "  1) opencode only"
echo "  2) Claude Code only"
echo "  3) Both opencode and Claude Code"
echo "  4) Skip (don't install skill)"
echo ""

read -r -p "Choose [1/2/3/4] (default: 3): " CHOICE
CHOICE="${CHOICE:-3}"

INSTALL_OPENCODE=false
INSTALL_CLAUDE=false

case "$CHOICE" in
    1) INSTALL_OPENCODE=true ;;
    2) INSTALL_CLAUDE=true ;;
    3) INSTALL_OPENCODE=true; INSTALL_CLAUDE=true ;;
    4) echo -e "${YELLOW}Skipping skill installation.${RESET}"; exit 0 ;;
    *) echo -e "${RED}Invalid choice. Exiting.${RESET}"; exit 1 ;;
esac

echo ""

# ── Install function ───────────────────────────────────────────────────
install_skill() {
    local dest="$1"
    local label="$2"

    mkdir -p "$dest"
    cp "$SKILL_SRC" "$dest/SKILL.md"

    if [ -f "$dest/SKILL.md" ]; then
        echo -e "  ${GREEN}✓${RESET} $label → $dest/SKILL.md"
    else
        echo -e "  ${RED}✗${RESET} Failed to write to $dest"
    fi
}

# ── opencode ───────────────────────────────────────────────────────────
if $INSTALL_OPENCODE; then
    echo -e "${BOLD}opencode:${RESET}"
    install_skill "$OPENCODE_GLOBAL" "global"
fi

# ── Claude Code ────────────────────────────────────────────────────────
if $INSTALL_CLAUDE; then
    echo -e "${BOLD}Claude Code:${RESET}"
    install_skill "$CLAUDE_GLOBAL" "global"
fi

# ── Summary ────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}✓ task-workflow skill installed${RESET}"
echo ""
echo "The AI will now see:"
echo "  Skill: task-workflow"
echo "  Description: Use the task CLI for AI agent task management"
echo ""
echo "To verify, run opencode and look for 'task-workflow' in available skills."
