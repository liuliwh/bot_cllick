"""此模块处理以命令行方式启动的浏览器,此浏览器带有文字与图像匹配功能.
注意:每次启动的浏览器均使用全新的profile.
Basic usage:
>>> import BrowserBot
>>> with BrowserBot.get('Firefox').open(some_url) as browser:
...  browser.click_by_word(
            "SetUserCookie", timeout=timeout, log_screenshot_folder=screenshot_folder
        )
     browser.click_by_img(img_path,confidence=0.7,
            timeout=10
        )
...
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from types import TracebackType
from typing import List, Mapping, Optional, Type

from easyprocess import EasyProcess, EasyProcessError

from bot_click import (
    BotClickError,
    ClickWithSendKeysMixin,
    ImgClickerMixin,
    ScreenshotMixin,
    TextClickerMixin,
    print_enhance_ocr_tip,
)

logger = logging.getLogger(__name__)


class BrowserBot(
    TextClickerMixin, ImgClickerMixin, ScreenshotMixin, ClickWithSendKeysMixin
):
    """Common parent class for managed Browsers. The browser has bot capability.
    支持上下文管理器，退出时会关闭浏览器进程以及清理生成的临时文件夹.
    若退出时，有未处理的BotClick错误，若传入SCREENSHOTS_FOLDER环境变量，
    则会进行截图并保存到对应目录中.
    若需要在退出时清理临时文件夹，请为self._managed_dir置值，为字符串全路径."""

    def __init__(
        self,
        cmd: List[str],
        extra_options: Optional[List[str]] = None,
    ) -> None:
        """新建浏览器实例，不会启动浏览器进程。是否启用新的profile取决于各子类.
        extra_options:命令行启动实例时，额外的命令行参数"""
        super().__init__()
        self._extra_options: List[str] = extra_options if extra_options else []
        self._cmd = cmd + self._extra_options
        self._proc: Optional[EasyProcess] = None
        self._managed_dir: Optional[str] = None

    @property
    def _userdata_cmd(self) -> Optional[List[str]]:
        """通过命令行启动参数传入userdata/profile."""
        return None

    def open(self, to: str) -> BrowserBot:
        """启动新的浏览器进程,并打开指定地址.
        注意：一个Browser进程实例只能open一次。要开启新的实例，须新建实例调用open"""
        if self._proc:
            raise RuntimeError("One proc can only start once.")
        self.start_url = to
        cmd = self._cmd
        if self._userdata_cmd:
            cmd += self._userdata_cmd
        cmd += [self.start_url]
        logger.info(f"Start process {cmd}")
        self._proc = EasyProcess(cmd).start()
        return self

    def close(self) -> None:
        """关闭浏览器以及停止浏览器进程.
        若浏览器使用了新建了profile/userdata,则会清理该临时目录."""
        if self._proc is None:
            logger.info("The process has been stopped")
            return
        logger.info(f"Stopping process. {self._proc}")
        try:
            self._proc.stop()
        except EasyProcessError:
            # EasyProcess use subprocess.Popen.kill(),
            # 所以只要Browser进程被kill了，就无所谓
            pass
        finally:
            self._proc = None
            self._clearnup()

    def _clearnup(self) -> None:
        if self._managed_dir:
            logger.info(f"Remove the managed folder. {self._managed_dir}")
            shutil.rmtree(self._managed_dir, ignore_errors=True)

    def __enter__(self) -> BrowserBot:
        """Use `with` statement."""
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_instance: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        """Use`with` statement,停止浏览器进程.
        若在with block里面有出现BotClickError,若传入SCREENSHOTS_FOLDER环境变量，则take screenshot,
        Propogate原有Exception"""
        # Handle and take screenshot first
        # https://docs.python.org/3/reference/datamodel.html#object.__exit__
        if exception_type and issubclass(exception_type, BotClickError):
            dir = os.environ.get("SCREENSHOTS_FOLDER", None)
            if dir:
                Path(dir).mkdir(exist_ok=True, parents=True)
            _, name = mkstemp(".png", prefix="browser_bot_", dir=dir)
            self.screenshot(name)
            logger.warning(
                f"Take screenshot {name} when exit with exception {exception_instance}"
            )
            print_enhance_ocr_tip()
        self.close()

    @classmethod
    def get(cls, name: str, extra_options: Optional[List[str]] = None) -> BrowserBot:
        """根据name新建浏览器实例，由各子类决定是否共用profile."""
        _class_map: Mapping[str, Type[BrowserBot]] = {
            "Firefox": Firefox,
            "Chrome": Chrome,
            "Chromium": Chromium,
        }
        cls_ = _class_map[name]
        return cls_(extra_options)  # type: ignore

    def __str__(self) -> str:
        return f"{self.__class__.__name__}:cmd={self._cmd},{self._userdata_cmd}"


class Firefox(BrowserBot):
    """受管理的Firefox,总是使用新的profile."""

    @property
    def _userdata_cmd(self) -> List[str]:
        # 仅在open的时候才会新建临时文件夹保存userdata,并且一个BrowserBot仅创建一次
        cmd = getattr(self, "_userdata_cmd_", None)
        if cmd is None:
            folder = mkdtemp()
            self._managed_dir = folder
            self._userdata_cmd_ = ["-profile", self._managed_dir]
        return self._userdata_cmd_

    def __init__(self, extra_options: Optional[List[str]] = None) -> None:
        """https://wiki.mozilla.org/Firefox/CommandLineOptions."""
        cmd = ["firefox", "-no-remote"]
        super().__init__(cmd, extra_options)


class _ChromeBase(BrowserBot):
    """受管理的Chrome/Chromium,总是使用新的profile."""

    def __init__(
        self, program_name: str, extra_options: Optional[List[str]] = None
    ) -> None:
        """Chrome更多启动项.
        https://peter.sh/experiments/chromium-command-line-switches/"""
        # https://askubuntu.com/questions/35392/how-to-launch-a-new-instance-of-google-chrome-from-the-command-line
        # 传递与每次新建--user-data-dir，主要是因为chrome默认会共用当前用户的session及进程,
        # 这样会导致测试环境不干净，相互干扰。
        # https://stackoverflow.com/questions/58993181/disable-chromium-can-not-update-chromium-window-notification
        cmd = [
            program_name,
            "--no-sandbox",
            "--ignore-certificate-errors",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-component-update",
            "--password-store=basic",
            # "--disable-save-password-bubble",
            "--simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT'",
        ]
        super().__init__(cmd, extra_options)

    @property
    def _userdata_cmd(self) -> List[str]:
        # 仅在open的时候才会新建临时文件夹保存userdata,并且一个BrowserBot仅创建一次
        cmd = getattr(self, "_userdata_cmd_", None)
        if cmd is None:
            folder = mkdtemp()
            self._managed_dir = folder
            self._userdata_cmd_ = [f"--user-data-dir={self._managed_dir}"]
        return self._userdata_cmd_


class Chrome(_ChromeBase):
    """受管理的Chrome,总是启用新的profile."""

    def __init__(self, extra_options: Optional[List[str]] = None) -> None:
        """Chrome: https://peter.sh/experiments/chromium-command-line-switches/ ."""
        super().__init__(
            program_name="google-chrome",
            extra_options=extra_options,
        )


class Chromium(_ChromeBase):
    """受管理的Chromium,总是启用新的profile."""

    def __init__(self, extra_options: Optional[List[str]] = None) -> None:
        """更多启动项，请查阅.
        https://peter.sh/experiments/chromium-command-line-switches/
        """
        super().__init__(
            program_name="chromium",
            extra_options=extra_options,
        )
