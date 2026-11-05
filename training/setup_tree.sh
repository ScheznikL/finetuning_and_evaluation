#!/usr/bin/env bash
# Build a runnable Hunyuan3D-2.1 tree: upstream at UPSTREAM_COMMIT + every file of manifest.txt
# placed back at its fork path.
#
# Usage: bash training/setup_tree.sh [BUILD_DIR] [--install]
#   BUILD_DIR defaults to ./build (git-ignored); --install also runs pip install -r requirements-train.txt
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$HERE")"
BUILD_DIR="${1:-$REPO_ROOT/build}"
UPSTREAM_URL="https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1"
UPSTREAM_COMMIT="$(head -n1 "$HERE/UPSTREAM_COMMIT")"

if [[ ! -d "$BUILD_DIR/.git" ]]; then
    git clone --no-checkout --filter=blob:none "$UPSTREAM_URL" "$BUILD_DIR"
fi
# core.longpaths: upstream has paths longer than Windows' default 260-character limit.
git -C "$BUILD_DIR" config core.longpaths true
git -C "$BUILD_DIR" checkout -q -f "$UPSTREAM_COMMIT"
if [[ -n "$(git -C "$BUILD_DIR" status --porcelain --untracked-files=no)" ]]; then
    echo "ERROR: upstream checkout in $BUILD_DIR is incomplete" >&2
    exit 1
fi
echo "Upstream at $(git -C "$BUILD_DIR" rev-parse --short HEAD)"

count=0
while read -r fork_path repo_path; do
    [[ -z "${fork_path:-}" || "$fork_path" == \#* ]] && continue
    mkdir -p "$BUILD_DIR/$(dirname "$fork_path")"
    cp "$REPO_ROOT/$repo_path" "$BUILD_DIR/$fork_path"
    count=$((count + 1))
done < "$HERE/manifest.txt"
echo "Overlaid $count files"

# Prompt sets are read by the generation scripts from experiments/.
mkdir -p "$BUILD_DIR/experiments"
cp "$REPO_ROOT"/evaluation/prompts/*.json "$BUILD_DIR/experiments/"

if [[ " $* " == *" --install "* ]]; then
    pip install -r "$HERE/requirements-train.txt"
fi

echo "Done. Next: source training/paths.env (HUNYUAN_DIR=$BUILD_DIR), then see training/README.md"
