"""用于处理Windows OS自带的浏览器启动与关闭."""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import mkstemp
from typing import Any, List, Mapping, Optional, Type

import cv2 as cv
from libs.browser_bot import BrowserBot

from bot_click import (
    BotClickError,
    NeedleIMGCriteria,
    NeedleNotFoundError,
    Point,
    print_enhance_ocr_tip,
)

logger = logging.getLogger(__name__)
module_needle_dir = Path(__file__).parent.absolute() / "needles"


class AbstractWindowsBrowserScreen(ABC):
    """Common parent class for windows browser family.
    支持上下文管理器with.
    当__exit__的时候，通过GUI点击x以关闭浏览器。但关闭浏览器以前，
    先检查是否有NeedleNotFoundError。
    若有,则先screenshot到环境变量SCREENSHOTS_FOLDER指定的路径。
    若无环境变量SCREENSHOTS_FOLDER，则存入临时文件夹。
    """

    def __init__(self, browser: BrowserBot) -> None:
        """给定browser，使其具备bot功能."""
        self.browser = browser

    @property
    def adddress_bar(self) -> Point:
        """根据地址栏needle信息，返回地址栏中心点位置."""
        return self.browser.locate_imgs(self._address_bar_needles, 60)  # type: ignore

    @property
    @abstractmethod
    def _logo(self) -> NeedleIMGCriteria:
        """Launch 浏览器时所需要的图像needle信息."""

    @property
    @abstractmethod
    def _address_bar_needles(self) -> List[NeedleIMGCriteria]:
        """定位浏览器地址栏."""

    @property
    @abstractmethod
    def _needle_close(self) -> NeedleIMGCriteria:
        """关闭窗口时所需要的图像needle信息."""

    def open(
        self, timeout: int = 120, log_screenshot_folder: Optional[Path] = None
    ) -> AbstractWindowsBrowserScreen:
        """通过UI启动浏览器."""

        self.browser.click_by_img(
            self._logo.path,
            self._logo.confidence,
            timeout=timeout,
            log_screenshot_folder=log_screenshot_folder,
        )
        return self

    def close(self, log_screenshot_folder: Optional[Path] = None) -> None:
        """关闭浏览器窗口."""
        logger.info("Close window")
        self.browser.click_by_img(
            self._needle_close.path,
            self._needle_close.confidence,
            timeout=10,
            log_screenshot_folder=log_screenshot_folder,
        )
        self._dismiss_close_all(log_screenshot_folder)

    def _dismiss_close_all(self, log_screenshot_folder: Optional[Path]) -> None:
        def _preprocess(image: cv.Mat) -> Any:
            """图像预处理."""
            img = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
            return cv.adaptiveThreshold(
                img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2
            )

        try:
            self.browser.click_by_word(
                "Close All",
                confidence=0.5,
                timeout=10,
                preprocess=_preprocess,
                log_screenshot_folder=log_screenshot_folder,
            )
        except NeedleNotFoundError:
            logger.info("No close all button, ingore")

    @classmethod
    def get(cls, name: str, browser: BrowserBot) -> AbstractWindowsBrowserScreen:
        """根据名称，将现有的screen转换成特定的screen子类.
        当与with使用时，退出with时，会关闭浏览器
        """
        _class_map: Mapping[str, Type[AbstractWindowsBrowserScreen]] = {
            "edge": _Windows10EdgeDesktopScreen,
            "ie11": _IE11DesktopScreen,
            "ie10": _IE10DesktopScreen,
            "ie9": IE9DesktopScreen,
            "ie8": _IE8DesktopScreen,
        }
        cls_ = _class_map[name]
        return cls_(browser)

    def __enter__(self) -> AbstractWindowsBrowserScreen:
        return self

    def __exit__(self, exc_type, exc, exc_tb):  # type: ignore
        # Handle and take screenshot first
        # 如果环境变量不存在，则存入临时文件夹
        if exc_type and issubclass(exc_type, BotClickError):
            dir = os.environ.get("SCREENSHOTS_FOLDER", None)
            if dir:
                Path(dir).mkdir(exist_ok=True, parents=True)
            name = mkstemp(".png", dir=dir, prefix="windows_exception")[1]
            self.browser.screenshot(name)
            logger.warning(f"Take screenshot {name} when exit with exception {exc}")
            print_enhance_ocr_tip()
        self.close()


class _IEDesktopScreen(AbstractWindowsBrowserScreen):
    _needle_dir = module_needle_dir / "ie"

    @property
    def _address_bar_needles(self) -> List[NeedleIMGCriteria]:
        return [
            NeedleIMGCriteria(self._needle_dir / "dropdown.png", 0.7),
            NeedleIMGCriteria(self._needle_dir / "next.png", 0.7),
        ]

    @property
    def _needle_close(self) -> NeedleIMGCriteria:
        return NeedleIMGCriteria(self._needle_dir / "close.png", 0.7)


class _Windows10EdgeDesktopScreen(AbstractWindowsBrowserScreen):
    _needle_dir = module_needle_dir / "edge"

    @property
    def _logo(self) -> NeedleIMGCriteria:
        # 由于 edge logo 区分度小，故用两侧logo来定位
        return NeedleIMGCriteria(self._needle_dir / "logo_launch.png", 0.9)

    @property
    def _address_bar_needles(self) -> List[NeedleIMGCriteria]:
        return [
            NeedleIMGCriteria(self._needle_dir / "home.png", 0.7),
            NeedleIMGCriteria(self._needle_dir / "settings.png", 0.7),
        ]

    @property
    def _needle_close(self) -> NeedleIMGCriteria:
        return NeedleIMGCriteria(self._needle_dir / "close.png", 0.99)


class _IE11DesktopScreen(_IEDesktopScreen):
    @property
    def _logo(self) -> NeedleIMGCriteria:
        return NeedleIMGCriteria(self._needle_dir / "logo_launch_ie9plus.png", 0.91)

    @property
    def _needle_close(self) -> NeedleIMGCriteria:
        return NeedleIMGCriteria(self._needle_dir / "close_ie11.png", 0.7)


class _IE10DesktopScreen(_IEDesktopScreen):
    @property
    def _logo(self) -> NeedleIMGCriteria:
        # IE logo 图像丰富，故识别率很高
        return NeedleIMGCriteria(self._needle_dir / "logo_launch_ie9plus.png", 0.91)


IE9DesktopScreen = _IE10DesktopScreen


class _IE8DesktopScreen(_IEDesktopScreen):
    @property
    def _logo(self) -> NeedleIMGCriteria:
        return NeedleIMGCriteria(self._needle_dir / "logo_launch_ie8.png", 0.7)
