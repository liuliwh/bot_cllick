"""bot_click mixins Libary.
本模块中的内容为bot_click的封装，目的是作为Mixin类扩展.
"""
import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import cv2 as cv

from . import bot_click
from .bot_click import Point

_DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))  # in sec
_DEFAULT_CHECK_INTERVAL = 5


class _CrossHairsMixin:
    """作为Mixin去使用，用于在指定画板上面指定点描绘crosshair."""

    def mark_crosshair(self, folder: Path, point: Point) -> Path:
        """将当前屏幕以及点击区域描述并保存到指定文件夹."""
        return bot_click.mark_crosshair(folder, point)


class _ClickWithCrossHairMixin(_CrossHairsMixin):
    """作为Mixin去使用，在click之前根据log_screenshot_folder判断是否需要crosshair."""

    def _handle_crosshair(
        self, folder_path: Optional[Path], point: Point
    ) -> Optional[Path]:
        """仅当folder_path才处理."""
        if folder_path:
            return self.mark_crosshair(folder=folder_path, point=point)
        return None

    def click(
        self,
        point: Point,
        duration: float = 0.4,
        log_screenshot_folder: Optional[Path] = None,
    ) -> None:
        """以指定速率移动鼠标到指定位置，并点击.
        在点击前，会根据log_screenshot_folder对screenshot并标注点击处"""
        self._handle_crosshair(log_screenshot_folder, point)
        bot_click.click(point, duration=duration)

    def double_click(
        self,
        point: Point,
        duration: float = 0.4,
        log_screenshot_folder: Optional[Path] = None,
    ) -> None:
        """以指定速率移动鼠标到指定位置，并双击.
        在点击前，会根据log_screenshot_folder对screenshot并标注点击处"""
        self._handle_crosshair(log_screenshot_folder, point)
        bot_click.double_click(point, duration=duration)


class ScreenshotMixin:
    """作为Mixin去使用,增加take screenshot功能."""

    def screenshot(self, file_path: str | Path) -> None:
        """Take screenshot返回保存文件路径."""
        bot_click.screenshot(file_path)


class _SendKeysMixin:
    """作为Mixin去使用，进行键盘输入."""

    def send_keys(
        self,
        message: str | List[str],
        append_enter: bool = False,
        log_screenshot_folder: Optional[Path] = None,
    ) -> None:
        """向当前鼠标位置发送按键.
        screenshot_folder:输入后screenshot的保存位置,默认不保存.
        append_enter: 是否需要在字串后面追回回车键.
        如:
        send_keys('abc',True): 生成键盘事件:['a','b','c','enter']
        send_keys('abc',False):生成键盘事件:['a','b','c']
        send_keys(['a','b','c','enter']):生成键盘事件:['a','b','c','enter']"""
        bot_click.send_keys(message, append_enter, log_screenshot_folder)

    def hotkey(self, *keys: Iterable[str]) -> None:
        """在当前位置控制组合键.
        Example: hotkey('ctrl', 'shift', 'c'):"Ctrl-Shift-C" shortcut press."""
        bot_click.hotkey(keys=keys)  # type: ignore


class ClickWithSendKeysMixin(_ClickWithCrossHairMixin, _SendKeysMixin):
    """带有Click以及键盘输入的Mixin."""

    def click_and_send_keys(
        self,
        message: str | List[str],
        point: Point,
        append_enter: bool = False,
        clear_before: bool = False,
        log_screenshot_folder: Optional[Path] = None,
    ) -> None:
        """在指定位置先点击，再输入字串.
        clear_before: 是否在输入字串之前，先点击编辑处，再发送ctl+a，以及backspace
        append_enter: 是否需要在字串后面追回回车键
        log_screenshot_folder:click之前截图并crosshair"""
        if clear_before:
            self.click(point, log_screenshot_folder=log_screenshot_folder)
            self.hotkey("ctrl", "a")
            self.send_keys(["backspace"])
        self.click(point, log_screenshot_folder=log_screenshot_folder)
        self.send_keys(message, append_enter, log_screenshot_folder)


class TextClickerMixin(_ClickWithCrossHairMixin):
    """作为Mixin去使用，用于等待，定位，点击指定单词."""

    def click_by_word(
        self,
        text: str,
        confidence: float = 0.7,
        timeout: int = _DEFAULT_TIMEOUT,
        duration: float = 0.4,
        log_screenshot_folder: Optional[Path] = None,
        ocr_config: str = "",
        preprocess: Optional[Callable[[cv.Mat], cv.Mat]] = None,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ) -> None:
        """在当前屏幕可见区域查找单个单词（以空格分隔)，并点击.
        定位方法与规则见locate_word的参数说明
        Raises: NeedleNotFoundException"""
        point = self.locate_word(
            text, confidence, timeout, ocr_config, preprocess, check_interval
        )
        self.click(point, duration, log_screenshot_folder)

    def locate_word(
        self,
        text: str,
        confidence: float = 0.7,
        timeout: int = _DEFAULT_TIMEOUT,
        ocr_config: str = "",
        preprocess: Optional[Callable[[cv.Mat], cv.Mat]] = None,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ) -> Point:
        """在当前屏幕可见区域查找单个单词（以空格分隔),返回confidence最高的.
        匹配前会按preprocess做图像预处理。处理后的必须是opencv可识别的，
        opencv使用BGR而不是RGB，所以，如果原图是RGB，则需要使用
        cv.cvtColor(image, cv.COLOR_RGB2BGR)或者转换为GRAY。
        ocr_config:默认自动识别.用于调整psm，如果主要是文字，且默认识别不高时，可--psm 4 或者
        --psm 6,或者是 --psm 11
        Refer:
        https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/
        Raises: NeedleNotFoundException"""
        return bot_click.locate_word(
            text,
            confidence,
            timeout,
            ocr_config=ocr_config,
            preprocess=preprocess,
            check_interval=check_interval,
        )


class ImgClickerMixin(_ClickWithCrossHairMixin):
    """作为Mixin去使用，用于等待，定位，点击指定图像needle."""

    def click_by_img(
        self,
        needle_path: Path,
        confidence: float = 0.7,
        duration: float = 0.4,
        timeout: int = _DEFAULT_TIMEOUT,
        log_screenshot_folder: Optional[Path] = None,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ) -> None:
        """在当前屏幕可见区域，查找与 needle 图像匹配度 >= confidence 的区域，并点击匹配区域中心.
        在点击之前，根据log_screenshot_folder的值决定是否将当前屏幕以及点击区域描述并保存到默认指定文件夹
        匹配时，参考locate_img

        confidence: [0, 1.0],
        duration: 移动鼠标时的速率
        log_screenshot_folder: 描述了点击区域的中间图像
        Raises: NeedleNotFoundException
        Reference:
        https://pyautogui.readthedocs.io/en/latest/screenshot.html#the-locate-functions

        """
        point = self.locate_img(needle_path, confidence, timeout, check_interval)
        self.click(point, duration, log_screenshot_folder)

    def locate_img(
        self,
        needle_path: Path,
        confidence: float = 0.7,
        timeout: int = _DEFAULT_TIMEOUT,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ) -> Point:
        """在当前屏幕可见区域，查找与 needle 图像匹配度 >= confidence 的区域,返回中心点.
        匹配方法：cv.matchTemplate,method是用TM_CCOEFF_NORMED。
        适用于rotation, scale, and viewing angle恒定的情况。
        Raises: NeedleNotFoundException"""
        return bot_click.locate_img(needle_path, confidence, timeout, check_interval)

    def locate_imgs(
        self,
        img_needles: List[bot_click.NeedleIMGCriteria],
        timeout: int,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ) -> Point:
        """在当前屏幕可见区域，查找与needles相匹配的中心点.
        Raises: NeedleNotFoundException"""
        points = [
            self.locate_img(needle.path, needle.confidence, timeout, check_interval)
            for needle in img_needles
        ]
        return bot_click.centroid(points)
