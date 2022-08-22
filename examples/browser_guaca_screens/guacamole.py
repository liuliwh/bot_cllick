"""用于处理Guacamole web GUI页面元素."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, ParamSpec

import cv2 as cv
from libs.browser_bot import BrowserBot

from bot_click.bot_click import NeedleNotFoundError

P = ParamSpec("P")

logger = logging.getLogger(__name__)


class GuacaLoginScreen:
    """用Firefox/Chromium来处理，Guacamole web 登录页面.
    用Chromium的原因为：
    可以通过policy以及命令行来控制password manager,以不显示save password界面，
    有助于提高后续界面的识别功能."""

    def __init__(self, browser: BrowserBot) -> None:
        """给定Browserbot."""
        self._browser = browser

    def _img_preprocess(self, img: cv.Mat) -> Any:
        image = cv.cvtColor(img, cv.COLOR_RGB2GRAY)
        return cv.threshold(image, 200, 255, cv.THRESH_BINARY)[1]

    def login(
        self,
        username: str,
        password: str,
        timeout: int,
        log_screenshot_folder: Optional[Path] = None,
    ) -> None:
        """登录guacamole页面."""
        # 将鼠标移出username输入框，使其失焦，以便定位元素
        self._browser.click_by_word(
            "APACHE", log_screenshot_folder=log_screenshot_folder
        )

        point = self._browser.locate_word(
            "Username", confidence=0.5, timeout=timeout, preprocess=self._img_preprocess
        )
        self._browser.click_and_send_keys(
            username,
            point=point,
            append_enter=False,
            log_screenshot_folder=log_screenshot_folder,
        )
        point = self._browser.locate_word(
            "Password", confidence=0.5, timeout=timeout, preprocess=self._img_preprocess
        )
        self._browser.click_and_send_keys(
            password,
            point=point,
            append_enter=True,
            log_screenshot_folder=log_screenshot_folder,
        )
        self._dimiss_savepassword()

    def _dimiss_savepassword(self) -> None:
        try:
            self._browser.locate_word(
                "Save password?", 0.5, timeout=60, preprocess=self._img_preprocess
            )
        except NeedleNotFoundError:
            """没有出现Save Password是期待现象"""
            pass
        else:
            """出现Save Password，提示异常，因为prompt可能会挡住窗口，
            影响后续测试."""
            raise RuntimeError(
                "Password Manager disable is not effective."
                "建议使用Chromium或者Firefox进行测试。使用Chrome时，启动项须添加"
                '"--incognito" For example :'
                "examples/test_browser_in_guca.py"
            )
