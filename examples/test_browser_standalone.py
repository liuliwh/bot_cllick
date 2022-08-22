"""The example to use bot_click to do the browser scrapy."""
import logging
import os
from pathlib import Path
from typing import Optional

from libs.utils import require_environ
from pyvirtualdisplay.display import Display

logger = logging.getLogger(__name__)


@require_environ(["BROWSER_NAME", "TESTWEB"])
def test_click_link(screenshots: Optional[Path]) -> None:
    """Test click link through the BrowserBot.
    说明：此样例中，import放在函数内的原因为：
    1. pyautogui依赖的mouseinfo，在引入与初始化时，依赖于环境变量DISPLAY,而该变量在
    VirutalDisplay新建实例之前是未知以及无法连接的.
    2. 使用IDE的自动补全功能.
    其它workaround的方法，见test_browser_in_guaca.py"""
    from libs.browser_bot import BrowserBot

    with BrowserBot.get(os.environ.get("BROWSER_NAME")).open(
        os.environ.get("TESTWEB")
    ) as browser:
        timeout = 60
        browser.click_by_word(
            "SetUserCookie", timeout=timeout, log_screenshot_folder=screenshots
        )
        browser.locate_word("AUTOMATED", timeout=timeout)
        logger.info("Done.")


if __name__ == "__main__":
    _DEBUG = os.environ.get("DEBUG", "0") == "1"
    logging.basicConfig(
        level=logging.DEBUG if _DEBUG else logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(lineno)d | %(message)s",
    )
    # 仅在_DEBUG 模式与 SCREENSHOTS_FOLDER 同时存在的时候，用例才会去记录crosshair
    # 非DEBUG 模式的时候，SCREENSHOTS_FOLDER 用于控制出现异常或者用例明确使用screenshot
    # 的时候使用
    _screenshoot_evn = os.environ.get("SCREENSHOTS_FOLDER", None)
    screenshot_folder = Path(_screenshoot_evn) if _screenshoot_evn and _DEBUG else None
    with Display(visible=False, size=(1200, 800), color_depth=24, use_xauth=True):
        test_click_link(screenshot_folder)
