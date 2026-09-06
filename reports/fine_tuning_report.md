# Enterprise University RAG - Domain Fine-Tuning & Quantization Report

## 1. Instruction Dataset Summary

- **Train Samples:** 16
- **Validation Samples:** 4
- **Prompt Schema:** Alpaca/ChatML with strict `<untrusted_academic_context>` fencing.

## 2. LoRA Adapter Specifications

- **Base Model:** `Qwen/Qwen2.5-7B-Instruct`
- **Rank ($r$):** 16
- **Alpha ($\alpha$):** 32
- **Target Projections:** `q_proj`, `k_proj`, `v_proj`, `o_proj`
- **Final Validation Loss:** 0.448

## 3. Quantization Deployment Profile

- **Format:** AWQ 4-bit (GEMM Kernel)
- **Memory Footprint:** 4.8 GB (down from 15.5 GB unquantized, ~3.2x compression)
- **vLLM Command:** `python3 -m vllm.entrypoints.openai.api_server --model models/quantized --quantization awq`
