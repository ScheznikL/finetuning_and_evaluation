#!/bin/bash
#SBATCH --job-name=gen_eval_pipeline
#SBATCH --output=logs/gen_eval_%j.log
#SBATCH --error=logs/gen_eval_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=48:00:00

# Generate one 100-prompt run, then evaluate it.
# Requires: training/setup_tree.sh has been run and training/paths.env is sourced (HUNYUAN_DIR, EVAL_OUT_DIR, ...).
# The checkpoint, run name, prior and condition-image zip are set in the __main__ block of
# generate_batch_from_text_initial_model.py (see training/README.md, "Generation"); RUN_NAME below must match it.

REPO_DIR="${REPO_DIR:?set REPO_DIR to the release repo root}"
RUN_NAME="${RUN_NAME:-batch_CKPT00008000_dit_v2_mm_detailed_100_res}"
PROMPTS_JSON="${PROMPTS_JSON:-$REPO_DIR/evaluation/prompts/in_prompts_MM.json}"
OUTPUT_DIR="${EVAL_OUT_DIR:?set EVAL_OUT_DIR}/${RUN_NAME}"

echo "========================================="
echo "STEP 1: Generating 3D models"
echo "========================================="

cd "${HUNYUAN_DIR:?path to the tree built by training/setup_tree.sh}"

python experiments/100/generate_batch_from_text_initial_model.py --prompt_dir "$PROMPTS_JSON"

# Check if generation succeeded
if [ $? -ne 0 ]; then
    echo "ERROR: Model generation failed!"
    exit 1
fi

echo "========================================="
echo "STEP 2: Running evaluation"
echo "========================================="

cd "$REPO_DIR/evaluation/metrics"

python evaluate_with_renders.py \
    --models_dir "${OUTPUT_DIR}/100_test_models" \
    --base_dir "${OUTPUT_DIR}" \
    --batch_name "${RUN_NAME}" \
    --output_metrics "${OUTPUT_DIR}/evaluation_results.json" \
    --clip_prompts_dir "$REPO_DIR/evaluation/prompts/in_prompts_MM_AUTO_CHOPPED.json" \
    --do_clip True

if [ $? -eq 0 ]; then
    echo "========================================="
    echo "Pipeline completed successfully!"
    echo "Results in: ${OUTPUT_DIR}"
    echo "========================================="
else
    echo "ERROR: Evaluation failed!"
    exit 1
fi
