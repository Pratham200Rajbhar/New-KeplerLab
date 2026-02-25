import logging
import threading
from contextlib import contextmanager
from typing import Optional

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

class GPUManager:
    """
    Singleton manager for coordination of GPU resources.
    Ensures that only one GPU-intensive task runs at a time to prevent OOM.
    """
    _instance: Optional['GPUManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GPUManager, cls).__new__(cls)
                    cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.gpu_lock = threading.Lock()
        self.has_gpu = torch is not None and torch.cuda.is_available()
        if self.has_gpu:
            logger.info(f"GPUManager initialized: Found {torch.cuda.get_device_name(0)}")
        else:
            logger.info("GPUManager initialized: No CUDA GPU detected")

    @contextmanager
    def gpu_session(self, task_name: str = "Generic Task"):
        """Context manager for exclusive access to the GPU."""
        if not self.has_gpu:
            yield
            return

        logger.info(f"Waiting for GPU lock: {task_name}")
        with self.gpu_lock:
            logger.info(f"Acquired GPU lock: {task_name}")
            try:
                self._clear_memory()
                yield
            finally:
                self._clear_memory()
                logger.info(f"Released GPU lock: {task_name}")

    def _clear_memory(self):
        """Aggressive GPU memory cleanup."""
        if self.has_gpu:
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            except Exception as e:
                logger.warning(f"Failed to clear GPU memory: {e}")

def get_gpu_manager() -> GPUManager:
    """Returns the GPUManager singleton."""
    return GPUManager()
