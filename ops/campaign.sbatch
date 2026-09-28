#!/bin/bash
#SBATCH --job-name=femlab-campaign
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --signal=B:TERM@120
#SBATCH --output=femlab-%j.log
set -euo pipefail
# Run sbatch from the reviewed checkout. Edit account/partition for YOUR cluster.
# Neither an allocation nor automatic requeue is created by committing this file.
# A second sbatch submission resumes the same directory and the same config.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
exec .venv/bin/python ops/worker.py \
  --config configs/mpm_smoke.json --run-dir outputs/hpc-campaign --max-hours 11
