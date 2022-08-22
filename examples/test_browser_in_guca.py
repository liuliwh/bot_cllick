"""The example uses browser_bot to launch Chromium and scarpy on the remote desktop."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from libs.utils import preprocess_embeded_testweb as prepress
from libs.utils import require_environ, vm_context
from pyvirtualdisplay import Display

logger = logging.getLogger(__name__)

# workaround for mouseinfo 初始化的时候DISPLAY未知或者无法连接
# 1. 先start VirtualDisplay,再引入pyautogui/mouseinfo依赖的包
disp = Display(visible=False, size=(1440, 900), color_depth=24, use_xauth=True).start()
from browser_guaca_screens import GuacaLoginScreen  # noqa: E402
from browser_guaca_screens import WindowsBrowserScreen  # noqa: E402
from libs.browser_bot import BrowserBot  # noqa: E402

# # 2. 通过atexit.register注册关闭display的handler.
# # 本module不会当成共用lib被其它modulee使用，所以不用这种方案

# 2. 在__main__函数中try finally中关闭即可，见__main__


@require_environ(["TESTWEB", "GUACA_URL", "BROWSER_NAME", "GUACA_BROWSER"])
@vm_context(os.environ.get("VM_RESTAPI"), os.environ.get("GUACA_BROWSER"))
def test_windows_browser(screenshots: Optional[Path]) -> None:
    """Test IE/Edge through remote desktop."""
    browser_name = os.environ.get("BROWSER_NAME")
    guaca_browser = guaca_user = os.environ.get("GUACA_BROWSER")
    guaca = os.environ.get("GUACA_URL")

    # Chrome doesn't honor policy PasswordManagerEnabled:false.
    # The Save Password bubble still show. Need to use --incognito.
    # Chromeium/FF is ok with policify file.
    # 注意：当使用incognito模式时，背景是黑色，ocr会有一定影响。
    # 故：推荐使用FF或者Chromium来测试Guacamole场景
    # extra_options = ["--incognito"] if browser_name == "Chrome" else None
    extra_options = None

    with BrowserBot.get(browser_name, extra_options).open(guaca) as browser:
        GuacaLoginScreen(browser).login(guaca_user, "test", 120, screenshots)
        with WindowsBrowserScreen.get(guaca_browser, browser).open(
            timeout=120, log_screenshot_folder=screenshots
        ) as win_browser:
            _test_action(win_browser, os.environ.get("TESTWEB", ""), screenshots)
            logger.info("Done")


def _test_action(
    action_browser: WindowsBrowserScreen, testweb: str, screenshots: Optional[Path]
) -> None:
    """在被测浏览器上面执行操作."""
    action_browser.browser.click_and_send_keys(
        testweb,
        point=action_browser.adddress_bar,
        append_enter=True,
        clear_before=True,
        log_screenshot_folder=screenshots,
    )
    action_browser.browser.click_by_word(
        "SetUserCookie",
        confidence=0.5,
        timeout=60,
        preprocess=prepress,
        log_screenshot_folder=screenshots,
    )
    action_browser.browser.locate_word(
        "AUTOMATED",
        timeout=60,
        preprocess=prepress,
    )


if __name__ == "__main__":
    _DEBUG = os.environ.get("DEBUG", "0") == "1"
    logging.basicConfig(
        level=logging.DEBUG if _DEBUG else logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(lineno)d | %(message)s",
    )
    _screenshoot_evn = os.environ.get("SCREENSHOTS_FOLDER", None)
    screenshots = Path(_screenshoot_evn) if _screenshoot_evn and _DEBUG else None

    try:
        test_windows_browser(screenshots)
    finally:
        disp.stop()
