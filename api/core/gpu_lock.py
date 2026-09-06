import threading

# Global process-wide GPU execution lock.
# Guarantees thread-safe PyTorch inference across concurrent student requests
# preventing CUDA stream races, memory fragmentation, and kernel collisions.
gpu_lock = threading.Lock()
