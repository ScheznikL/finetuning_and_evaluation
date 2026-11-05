#!/usr/bin/env bash
# Copy the files listed in manifest.txt from a Hunyuan3D-2.1 fork checkout into this repository.
# Hard-coded cluster paths in shell/sbatch/yaml files are replaced by environment variables
# (see paths.env.example); Python files are copied unchanged.
#
# Usage: bash training/sync_from_fork.sh /path/to/Hunyuan3D-2.1
set -euo pipefail

FORK_DIR="${1:?usage: $0 /path/to/Hunyuan3D-2.1 fork}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$HERE")"

# Longest prefixes first.
subst_paths() {
    sed -i \
        -e 's#/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2\.1#${HUNYUAN_DIR}#g' \
        -e 's#/dcs/pg24/u5745134/Desktop/dev#${DEV_DIR}#g' \
        -e 's#/dcs/large/u5745134/evaluation_test/testing_Hunuyuan3d#${EVAL_OUT_DIR}#g' \
        -e 's#/dcs/large/u5745134/train_results#${TRAIN_RESULTS_DIR}#g' \
        -e 's#/dcs/large/u5745134/hy3dgen_models#${MODELS_DIR}#g' \
        -e 's#/dcs/large/u5745134/cache/huggingface#${HF_CACHE_DIR}#g' \
        -e 's#/dcs/large/u5745134/dataset#${DATA_ROOT}#g' \
        -e 's#/dcs/large/u5745134#${WORK_DIR}#g' \
        "$1"
}

# OmegaConf resolves ${oc.env:VAR}, not ${VAR}.
subst_paths_yaml() {
    subst_paths "$1"
    sed -i -E 's#\$\{([A-Z_]+)\}#${oc.env:\1}#g' "$1"
}

count=0
missing=()
while read -r src dst; do
    [[ -z "${src:-}" || "$src" == \#* ]] && continue
    if [[ ! -f "$FORK_DIR/$src" ]]; then
        missing+=("$src")
        continue
    fi
    mkdir -p "$REPO_ROOT/$(dirname "$dst")"
    cp "$FORK_DIR/$src" "$REPO_ROOT/$dst"
    case "$dst" in
        *.sh|*.sbatch) subst_paths "$REPO_ROOT/$dst" ;;
        *.yaml)        subst_paths_yaml "$REPO_ROOT/$dst" ;;
    esac
    count=$((count + 1))
done < "$HERE/manifest.txt"

{
    echo "source_dir: $FORK_DIR"
    echo "source_commit: $(git -C "$FORK_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "source_dirty: $(git -C "$FORK_DIR" status --porcelain -- hy3dshape experiments batchcompute_scripts 2>/dev/null | grep -c '^ M' || true) modified tracked files"
    echo "synced_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "files: $count"
} > "$HERE/SYNC_INFO"

echo "Copied $count files from $FORK_DIR"
if (( ${#missing[@]} )); then
    echo "Missing in fork (not copied):"
    printf '  %s\n' "${missing[@]}"
    exit 1
fi
