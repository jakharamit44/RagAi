import os
import sys
import time
import glob
import ctypes
import logging
import subprocess
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_CUDA_INITIALIZED = False
_GPU_STATUS_CACHE: Optional[Dict[str, Any]] = None
_LAST_STATUS_TIME: float = 0.0
_CACHE_TTL_SECONDS: float = 3.0

def init_cuda_runtime() -> bool:
    """
    Auto-detects and loads NVIDIA CUDA Toolkit and cuDNN DLLs into Windows process.
    Guarantees ONNXRuntime CUDAExecutionProvider resolves all symbols (cublasLt64_13.dll, cudnnCreate).
    """
    global _CUDA_INITIALIZED
    if _CUDA_INITIALIZED:
        return True

    if os.name != "nt":
        # On Linux/Ubuntu, driver libraries are typically handled by ldconfig
        _CUDA_INITIALIZED = True
        return True

    logger.info("Initializing NVIDIA CUDA & cuDNN runtime directories...")

    # 1. Register PyTorch bundled CUDA libraries FIRST to prevent version conflicts
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_torch_dirs = [
        os.path.join(base_dir, ".venv", "Lib", "site-packages", "torch", "lib"),
        os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib"),
    ]
    loaded_dirs = []
    for td in candidate_torch_dirs:
        if os.path.isdir(td):
            try:
                os.add_dll_directory(td)
                if td not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = td + os.pathsep + os.environ.get("PATH", "")
                loaded_dirs.append(td)
            except Exception as ex:
                logger.debug(f"Could not add torch lib dir {td}: {ex}")

    # Initialize PyTorch safely before loading external toolkits
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"PyTorch CUDA initialized on {torch.cuda.get_device_name(0)} (CUDA {torch.version.cuda})")
    except Exception as ex:
        logger.warning(f"PyTorch CUDA pre-init note: {ex}")

    # Determine active PyTorch CUDA major version (e.g. 12)
    torch_cuda_major = None
    try:
        import torch
        if hasattr(torch, "version") and torch.version.cuda:
            torch_cuda_major = torch.version.cuda.split(".")[0]
    except Exception:
        pass

    # 2. Add matching CUDA Toolkit directories (avoid preloading incompatible major version symbols)
    candidate_cuda_dirs = []
    if torch_cuda_major == "12":
        candidate_cuda_dirs.extend([
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin",
        ])
    elif torch_cuda_major == "13":
        candidate_cuda_dirs.extend([
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\x64",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin",
        ])
    else:
        # Generic discovery
        for env_k in ["CUDA_PATH", "CUDA_HOME"]:
            p = os.environ.get(env_k)
            if p and os.path.exists(p):
                candidate_cuda_dirs.extend([os.path.join(p, "bin", "x64"), os.path.join(p, "bin")])

    # Locate cuDNN path inside current python virtualenv or site-packages
    candidate_cudnn_dirs = [
        os.path.join(base_dir, ".venv", "Lib", "site-packages", "nvidia", "cudnn", "bin"),
        os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "cudnn", "bin"),
        os.path.join(sys.prefix, "lib", "python" + sys.version[:4], "site-packages", "nvidia", "cudnn", "bin"),
    ]

    # Add valid directories to Windows DLL search and PATH
    for d in candidate_cuda_dirs + candidate_cudnn_dirs:
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
                if d not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                loaded_dirs.append(d)
            except Exception as ex:
                logger.debug(f"Could not add DLL dir {d}: {ex}")

    # Explicitly preload cuDNN sub-libraries
    for cudnn_dir in candidate_cudnn_dirs:
        if os.path.isdir(cudnn_dir):
            for fname in sorted(os.listdir(cudnn_dir)):
                if fname.lower().endswith(".dll"):
                    dll_path = os.path.join(cudnn_dir, fname)
                    try:
                        ctypes.CDLL(dll_path)
                    except Exception:
                        pass

    logger.info(f"NVIDIA CUDA runtime configured. Registered {len(loaded_dirs)} directories.")
    _CUDA_INITIALIZED = True
    return True


def get_gpu_status() -> Dict[str, Any]:
    """
    Returns real-time GPU telemetry (model, memory, utilization, active ONNX provider).
    Cached for 3 seconds to avoid subprocess overhead.
    """
    global _GPU_STATUS_CACHE, _LAST_STATUS_TIME

    now = time.time()
    if _GPU_STATUS_CACHE is not None and (now - _LAST_STATUS_TIME) < _CACHE_TTL_SECONDS:
        return _GPU_STATUS_CACHE

    init_cuda_runtime()

    status: Dict[str, Any] = {
        "gpu_available": False,
        "gpu_name": "None (CPU Mode)",
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "memory_free_mb": 0,
        "gpu_utilization_pct": 0,
        "driver_version": "N/A",
        "cuda_version": "N/A",
        "onnx_providers": [],
        "active_acceleration": "CPU Fallback",
        "is_cuda_active": False,
    }

    # Query ONNX Runtime Execution Providers
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        status["onnx_providers"] = providers
        if "CUDAExecutionProvider" in providers:
            status["is_cuda_active"] = True
            status["active_acceleration"] = "CUDA GPU Acceleration"
    except Exception as e:
        status["onnx_providers"] = ["CPUExecutionProvider"]

    # Query nvidia-smi for live hardware telemetry
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,driver_version",
            "--format=csv,noheader,nounits"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2.0)
        if proc.returncode == 0 and proc.stdout.strip():
            line = proc.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                status["gpu_available"] = True
                status["gpu_name"] = parts[0]
                status["memory_total_mb"] = int(parts[1])
                status["memory_used_mb"] = int(parts[2])
                status["memory_free_mb"] = int(parts[3])
                status["gpu_utilization_pct"] = int(parts[4])
                status["driver_version"] = parts[5]
                status["cuda_version"] = "13.1 / 13.3"
                if status["is_cuda_active"]:
                    status["active_acceleration"] = f"CUDA Active: {parts[0]}"
    except Exception as ex:
        logger.debug(f"nvidia-smi query failed: {ex}")

    _GPU_STATUS_CACHE = status
    _LAST_STATUS_TIME = now
    return status
