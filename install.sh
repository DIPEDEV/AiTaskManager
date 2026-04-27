#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)       echo "unknown" ;;
    esac
}

detect_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null && "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            echo "$cmd"
            return
        fi
    done
    echo ""
}

find_bin_dir() {
    local os="$1"
    case "$os" in
        linux|macos)
            if [ -w /usr/local/bin ]; then
                echo "/usr/local/bin"
            elif [ -d "$HOME/.local/bin" ] || mkdir -p "$HOME/.local/bin" 2>/dev/null; then
                echo "$HOME/.local/bin"
            else
                echo "$HOME/.local/bin"
            fi
            ;;
        windows)
            if [ -d "$HOME/bin" ] || mkdir -p "$HOME/bin" 2>/dev/null; then
                echo "$HOME/bin"
            else
                echo "$HOME"
            fi
            ;;
    esac
}

ensure_path() {
    local bin_dir="$1"
    local shell_rc=""

    case "$SHELL" in
        */zsh) shell_rc="$HOME/.zshrc" ;;
        */bash) shell_rc="$HOME/.bashrc" ;;
        *) shell_rc="$HOME/.profile" ;;
    esac

    if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
        echo -e "${YELLOW}Adding $bin_dir to PATH in $shell_rc${RESET}"
        echo "export PATH=\"$bin_dir:\$PATH\"" >> "$shell_rc"
        echo -e "${YELLOW}Run 'source $shell_rc' or restart your shell${RESET}"
    fi
}

echo -e "${BOLD}task CLI installer${RESET}"
echo ""

OS=$(detect_os)
echo -e "Detected OS: ${GREEN}$OS${RESET}"

PYTHON=$(detect_python)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}Python 3.10+ not found. Install it first.${RESET}"
    exit 1
fi
echo -e "Python:      ${GREEN}$($PYTHON --version)${RESET}"

BIN_DIR=$(find_bin_dir "$OS")
echo -e "Install to:  ${GREEN}$BIN_DIR${RESET}"
echo ""

# Install
echo "Installing task CLI..."

# Try pipx first (isolated, recommended)
if command -v pipx &>/dev/null; then
    echo "Using pipx..."
    pipx install -e "$SCRIPT_DIR" --force 2>/dev/null && {
        TASK_BIN="$HOME/.local/bin/task"
    }
# Fallback: system pip directly
elif $PYTHON -m pip install --break-system-packages -e "$SCRIPT_DIR" --quiet 2>/dev/null; then
    TASK_BIN="$HOME/.local/bin/task"
# Last resort: user install
elif $PYTHON -m pip install -e "$SCRIPT_DIR" --user --quiet 2>/dev/null; then
    TASK_BIN="$HOME/.local/bin/task"
else
    echo -e "${RED}Installation failed.${RESET}"
    exit 1
fi

# Ensure task binary exists
if [ ! -f "$TASK_BIN" ]; then
    # Find it
    TASK_BIN=$(which task 2>/dev/null || echo "")
    if [ -z "$TASK_BIN" ]; then
        echo -e "${RED}Could not find installed 'task' binary.${RESET}"
        exit 1
    fi
fi

chmod +x "$TASK_BIN" 2>/dev/null || true

# Symlink only if pip didn't already put task in BIN_DIR
TASK_REAL=$(readlink -f "$TASK_BIN" 2>/dev/null || echo "$TASK_BIN")
LINK_PATH="$BIN_DIR/task"
LINK_REAL=$(readlink -f "$LINK_PATH" 2>/dev/null || echo "")

if [ "$TASK_REAL" != "$LINK_REAL" ] && [ "$TASK_BIN" != "$LINK_PATH" ]; then
    if [ -L "$LINK_PATH" ] || [ -f "$LINK_PATH" ]; then
        echo -e "${YELLOW}Replacing existing task at $LINK_PATH...${RESET}"
        rm -f "$LINK_PATH"
    fi
    ln -sf "$TASK_BIN" "$LINK_PATH" 2>/dev/null || {
        echo "Cannot symlink, copying instead..."
        cp "$TASK_BIN" "$LINK_PATH"
    }
    chmod +x "$LINK_PATH" 2>/dev/null || true
fi

ensure_path "$BIN_DIR"

echo ""
echo -e "${GREEN}${BOLD}✓ task CLI installed${RESET}"
echo ""

# ── Skill installation ──────────────────────────────────────────────────
SKILL_INSTALLER="$SCRIPT_DIR/install-skill.sh"
if [ -f "$SKILL_INSTALLER" ]; then
    echo -e "${CYAN}▶ AI agent skill (task-workflow)${RESET}"
    echo -e "  This teaches opencode / Claude Code how to use the task CLI."
    echo ""
    read -r -p "  Run skill installer? [Y/n] " SKILL_ANSWER
    SKILL_ANSWER="${SKILL_ANSWER:-y}"
    if [[ "$SKILL_ANSWER" =~ ^[Yy]$ ]]; then
        echo ""
        bash "$SKILL_INSTALLER"
    fi
fi

echo ""
echo "Test it:  task"
echo "Init:     task init"
printf "Help:     task --help\n"
