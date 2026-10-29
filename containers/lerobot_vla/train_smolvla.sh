#!/usr/bin/env bash
set -euo pipefail

ANOMALY_ID="${1:-skydrol_spill}"
echo "[AETHER-LOOP Computer 1] Launching LeRobot SmolVLA Fine-Tuning on Nebius Serverless H100..."

lerobot-train \
  --policy.type=smolvla \
  --policy.repo_id="aether-loop/smolvla-${ANOMALY_ID}" \
  --policy.input_features=null \
  --policy.output_features=null \
  --dataset.root="/data/sdg/${ANOMALY_ID}" \
  --batch_size=64 \
  --num_workers=8 \
  --epochs=12 \
  --rename_map='{"observation.images.camera_ego_rgb": "observation.images.ego_view"}'

