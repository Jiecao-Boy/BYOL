#!/bin/bash

#SBATCH --job-name=BYOL_test
#SBATCH --output=/scratch/yd2032/Desktop/output/train_1.out 
#SBATCH --error=/scratch/yd2032/Desktop/output/train_1.err
#SBATCH --export=ALL
#SBATCH --time=24:00:00
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=200GB
#SBATCH -c 24

#SBATCH --mail-type=END
#SBATCH --mail-user=sa5914@nyu.edu

singularity exec --nv \
--overlay $SCRATCH/overlay-50G-10M.ext3:ro \
/scratch/work/public/singularity/cuda11.2.2-cudnn8-devel-ubuntu20.04.sif \
/bin/bash -c "
source /ext3/env.sh
conda activate tactile_dexterity
cd /scratch/yd2032/Desktop/byol_implementation/BYOL
python train.py 
"