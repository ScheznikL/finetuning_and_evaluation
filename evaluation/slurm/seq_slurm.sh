#!/bin/bash
#SBATCH --job-name=gen_eval_pipeline
#SBATCH --output=logs/gen_eval_%j.log
#SBATCH --error=logs/gen_eval_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=48:00:00

# Configuration
CHECKPOINT_NAME="${CHECKPOINT_NAME:-CKPT00008000}"
CHECKPOINT_PATH="${CHECKPOINT_PATH:?path to ckpt-step=XXXXXXXX.ckpt}"
OUTPUT_DIR="${DATA_DIR:?set DATA_DIR}/batch_${CHECKPOINT_NAME}_100_res"

echo "========================================="
echo "STEP 1: Generating 3D models"
echo "========================================="

cd "${HUNYUAN_DIR:?path to the Hunyuan3D-2.1 fork}"

python test_checkpoint_batch.py

# Check if generation succeeded
if [ $? -ne 0 ]; then
    echo "ERROR: Model generation failed!"
    exit 1
fi

echo "========================================="
echo "STEP 2: Running evaluation"
echo "========================================="

# Run your evaluation script here
python evaluate_batch.py \
    --models_dir ${OUTPUT_DIR}/models \
    --output_metrics ${OUTPUT_DIR}/evaluation_results.json

if [ $? -eq 0 ]; then
    echo "========================================="
    echo "Pipeline completed successfully!"
    echo "Results in: ${OUTPUT_DIR}"
    echo "========================================="
else
    echo "ERROR: Evaluation failed!"
    exit 1
fi