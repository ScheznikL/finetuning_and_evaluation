#!/bin/bash
#
#SBATCH --job-name=evaluate-gpu  # Job name for tracking
#SBATCH --partition=eagle       # Partition you wish to use (see above for list)
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6       # Number of CPU threads used by your job
#SBATCH --gres=gpu:1            # Number of GPUs to use 
#SBATCH --time=2-00:00:00       # Job time limit set to 2 days (48 hours)
#
#SBATCH --mail-type=END,FAIL,TIME_LIMIT_80 # Events to send email on, remove if you don't want this
#SBATCH --output=eval_withim_pr_joboutput_eagle%j.out # Standard out from your job
#SBATCH --error=eval_withim_pr_joboutput_eagle%j.err  # Standard error from your job

## Initialisation ##
source /etc/profile.d/modules.sh
source /etc/profile.d/conda.sh

cd "${REPO_DIR:?set REPO_DIR to the release repo root}/evaluation/metrics"
conda activate hunyuan3d_eval

module load Blender/4.2.1
module load CUDA/13.0.2

export OPENCV_IO_ENABLE_OPENEXR=1
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

python ./evaluate_with_renders.py "$@"   # see EVAL.md section 6 for arguments