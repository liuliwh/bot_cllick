"""The utility module provided for examples."""
from __future__ import annotations

import contextlib
import logging
import os
from functools import wraps
from typing import Any, Callable, List, Optional, ParamSpec, TypeVar
from urllib.request import urlopen

import cv2 as cv

logger = logging.getLogger(__name__)

F = TypeVar("F")
P = ParamSpec("P")


def require_environ(envs: List[str]) -> Callable[[Callable[P, F]], Callable[P, F]]:
    """用于function wrapper，验证环境变量是否已设置，空串认为是有效的.
    Raises: ValueError."""

    def decorator(func: Callable[P, F]) -> Callable[P, F]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> F:
            validate_environ(envs=envs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_environ(envs: List[str]) -> None:
    """检查环境变量是否有设置。空串也认为是有效的.
    Raises: ValueError"""
    for name in envs:
        value = os.environ.get(name)
        if value is None:
            raise ValueError(f"environment with {name} should be set")


def preprocess_embeded_testweb(image: cv.Mat) -> Any:
    """当testweb嵌入到多个浏览器时，需要预处理以提高ocr准确度."""
    img = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
    return cv.adaptiveThreshold(
        img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2
    )


class vm_context(contextlib.ContextDecorator):
    """开启与关闭vm."""

    def __init__(
        self, vmananager_server: Optional[str] = None, vm_key: Optional[str] = None
    ) -> None:
        """vmananager_server: 监听开启与关闭的rest api server."""
        super().__init__()
        self.vm_manager = vmananager_server
        self.vm_key = vm_key

    def __enter__(self) -> vm_context:
        """开启vm.
        Raises: urllib.error.HTTPError"""
        if self.vm_manager is None or self.vm_key is None:
            logger.warning(
                """The vm is not managed by the script, please start/stop vm manually.
                Or. specify the restapi server to start and stop the vm"""
            )
            return self
        url = f"{self.vm_manager}/vms/{self.vm_key}/start"
        with urlopen(url, data=b"", timeout=120) as resp:
            logger.info(f'Start vm: {resp.read().decode("utf-8")}')
        return self

    def __exit__(self, exc_type, exc, exc_tb):  # type: ignore
        """关闭vm.
        Raises: urllib.error.HTTPError"""
        if self.vm_manager is None or self.vm_key is None:
            logger.warning("The vm is not managed by the script,ignore.")
        else:
            url = f"{self.vm_manager}/vms/{self.vm_key}/stop"
            with urlopen(url, data=b"", timeout=120) as resp:
                logger.info(f'Stop vm: {resp.read().decode("utf-8")}')
