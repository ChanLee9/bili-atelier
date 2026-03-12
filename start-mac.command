#!/bin/bash

set -euo pipefail

project_root="$(cd "$(dirname "$0")" && pwd)"
cd "$project_root"

assert_command() {
  local name="$1"
  local install_hint="$2"

  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command '$name'. $install_hint" >&2
    exit 1
  fi
}

get_file_text_or_empty() {
  local path="$1"

  if [[ -f "$path" ]]; then
    tr -d '[:space:]' < "$path"
  fi
}

escape_for_osascript() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

assert_command "python3" "Please install Python 3 and make sure it is available in PATH."
assert_command "pnpm" "Please install pnpm and make sure it is available in PATH."
assert_command "osascript" "AppleScript support is required on macOS to open Terminal windows."

venv_path="$project_root/.venv"
venv_python="$venv_path/bin/python"
requirements_path="$project_root/api/requirements.txt"
requirements_hash_path="$venv_path/.requirements.hash"
frontend_modules_path="$project_root/node_modules"
frontend_platform_stamp_path="$frontend_modules_path/.platform-stamp"
current_frontend_platform="$(uname -s)-$(uname -m)"

if [[ ! -x "$venv_python" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$venv_path"
fi

saved_frontend_platform="$(get_file_text_or_empty "$frontend_platform_stamp_path")"

if [[ ! -d "$frontend_modules_path" || "$saved_frontend_platform" != "$current_frontend_platform" ]]; then
  echo "Installing frontend dependencies..."
  pnpm install
  printf '%s\n' "$current_frontend_platform" > "$frontend_platform_stamp_path"
fi

current_requirements_hash="$(shasum -a 256 "$requirements_path" | awk '{print $1}')"
saved_requirements_hash="$(get_file_text_or_empty "$requirements_hash_path")"

if [[ "$saved_requirements_hash" != "$current_requirements_hash" ]]; then
  echo "Syncing backend dependencies..."
  "$venv_python" -m pip install -r "$requirements_path"
  printf '%s\n' "$current_requirements_hash" > "$requirements_hash_path"
fi

escaped_project_root="$(escape_for_osascript "$project_root")"
escaped_venv_python="$(escape_for_osascript "$venv_python")"

backend_command="cd \\\"$escaped_project_root\\\"; \\\"$escaped_venv_python\\\" -m uvicorn api.app.main:app --reload --host 127.0.0.1 --port 8000"
frontend_command="cd \\\"$escaped_project_root\\\"; pnpm dev:web"

echo "Starting backend at http://127.0.0.1:8000 ..."
echo "Starting frontend..."

osascript <<EOF
tell application "Terminal"
    activate
    do script "$backend_command"
    do script "$frontend_command"
end tell
EOF

echo
echo "Frontend should be available at http://127.0.0.1:5173"
echo "Backend should be available at http://127.0.0.1:8000"
