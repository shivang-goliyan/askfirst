#!/usr/bin/env bash
# Serve one open model with vLLM on a single AMD MI300X.
#
# Single GPU on purpose. Tensor parallelism across four cards would cost 4x the hours for a
# sustained window, and the whole credit allocation is about 300 GPU-hours at $1.99 each. One
# card has 192GB, which is plenty for a 7-8B model with room for a long context.
#
# Run this ON the droplet, inside the ROCm container.
set -euo pipefail

MODEL="${ASKFIRST_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${PORT:-8000}"

# AITER is AMD's fused-kernel library; the vLLM ROCm recipes turn it on explicitly.
export VLLM_ROCM_USE_AITER="${VLLM_ROCM_USE_AITER:-1}"
export HIP_VISIBLE_DEVICES="${HIP_VISIBLE_DEVICES:-0}"

echo "model      $MODEL"
echo "port       $PORT"
echo "gpu        $(rocm-smi --showproductname 2>/dev/null | grep -m1 -i card || echo 'rocm-smi not found')"
echo

# --max-logprobs matters for us specifically: the scorer reads logprobs over the prompt, and the
# server refuses requests asking for more than this.
exec vllm serve "$MODEL" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --max-model-len 8192 \
  --max-logprobs 20 \
  --dtype bfloat16 \
  --disable-log-requests
