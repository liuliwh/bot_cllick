"""Core module of bot_click. It provides utility to do ocr and image recognition.
若使用class的话，推荐使用mixins module中提供的Mixin类。
由于pyautogui依赖包中需要DISPLAY,若使用VirtualDisplay的话，需要先建Display.
>>> import bot_click
>>> # New Display and start some UI app
>>> bot_click.click_by_word(text, confidence=0.7, timeout=30)
>>> # OCR with customization
>>> bot_click.click_by_word(text, confidence=0.7, timeout=30,preprocess=somefunction)
>>> bot_click.click_by_img(img_path,confidence=0.8,timeout=10)
>>> bot_click.click_and_send_keys('hello')
>>> bot_click.screenshot(folder_path)
"""
import collections
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import cv2 as cv
import numpy as np
import pyautogui
import pytesseract
from numpy.typing import NDArray
from PIL import Image, ImageGrab

Point = collections.namedtuple("Point", ["x", "y"])
NeedleIMGCriteria = collections.namedtuple("NeedleIMGCriteria", ["path", "confidence"])
_TesseractMatchResult = collections.namedtuple(
    "_TesseractMatchResult",
    ["text", "block_num", "confidence", "left", "top", "width", "height"],
)

_DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))  # in sec
_DEFAULT_CHECK_INTERVAL = 5

logger = logging.getLogger(__name__)


class BotClickError(Exception):
    """Base-class for all exceptions raised by this module."""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.args!r})"


class NeedleNotFoundError(BotClickError):
    """根据Needle 没定位到元素."""

    pass


def click(point: Optional[Point] = None, duration: float = 0.4) -> None:
    """以指定速率移动鼠标到指定位置，并点击.
    point:为None时，则为当前鼠标所在位置.
    """
    point = point or position()
    pyautogui.click(x=point.x, y=point.y, duration=duration)
    logger.info(f"click at point={point}")


def double_click(point: Optional[Point] = None, duration: float = 0.4) -> None:
    """以指定速率移动鼠标到指定位置，并双击.
    point:为None时，则为当前鼠标所在位置.
    """
    point = point or position()
    pyautogui.doubleClick(x=point.x, y=point.y, duration=duration)
    logger.info(f"doubleclick at point={point}")


def position() -> Point:
    """当前鼠标位置."""
    return Point(*pyautogui.position())


def centroid(points: List[Point]) -> Point:
    """给定一组2D坐标，返回中点."""
    sum_x = sum(p.x for p in points)
    sum_y = sum(p.y for p in points)
    result = Point(x=(sum_x // len(points)), y=(sum_y // len(points)))
    logger.info(f"centroid is {result} for {points}")
    return result


def hotkey(keys: Iterable[str]) -> None:
    """发送组合键."""
    pyautogui.hotkey(keys=keys)


def send_keys(
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
    tosend = message
    # 为True时，转为list传送.转换规则为：
    # 1.原message为str，则变为list(message)+['enter']
    # 2.原message为List[str]时，则[message]+['enter']
    if append_enter:
        if type(message) == str:
            tosend = list(message) + ["enter"]
        else:
            tosend += ["enter"]  # type: ignore
    logger.info(f"to enter {tosend}")
    pyautogui.write(message=tosend, interval=0.1)
    if log_screenshot_folder:
        file_path = log_screenshot_folder / gen_filename()
        screenshot(file_path)
        logger.info(f"Screenshot saved to {file_path}")


def screenshot(file_path: str | Path) -> None:
    """Take screenshot and save to file."""
    ImageGrab.grab().save(file_path)


def gen_filename(ext: str = "png") -> str:
    """生成human readable 基于日期的文件名."""
    now = datetime.now()
    filename = "{}-{}-{}_{}-{}-{}-{}.{}".format(
        now.year,
        str(now.month),
        str(now.day),
        now.hour,
        now.minute,
        now.second,
        str(now.microsecond)[:3],
        ext,
    )
    return filename


def _draw_crosshair(img_cv: cv.Mat, point: Point) -> cv.Mat:
    """在给定opencv兼容的画板image上的指定点，描绘x,返回描绘后的Mat图像."""
    cv.drawMarker(
        img_cv,
        point,
        color=(255, 0, 255),
        markerType=cv.MARKER_CROSS,
        markerSize=40,
        thickness=2,
    )
    return img_cv


def _screenshot_ndarray() -> NDArray[np.uint8]:
    """Take screenshot并转换成opencv格式."""
    return np.array(ImageGrab.grab())


def mark_crosshairs(folder: Path, points: List[Point]) -> Path:
    """将当前屏幕以及点击区域描述并保存到指定文件夹."""
    cv_img = _screenshot_ndarray()
    for point in points:
        cv_img = _draw_crosshair(cv_img, point)
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder.absolute() / gen_filename()
    cv.imwrite(str(file_path), cv_img)
    logger.info(f"save the crosshair to {file_path}")
    return file_path


def mark_crosshair(folder: Path, point: Point) -> Path:
    """将当前屏幕以及点击区域描述并保存到指定文件夹."""
    return mark_crosshairs(folder, [point])


def click_by_img(
    needle_path: Path,
    confidence: float = 0.7,
    duration: float = 0.4,
    timeout: int = _DEFAULT_TIMEOUT,
    check_interval: int = _DEFAULT_CHECK_INTERVAL,
) -> None:
    """在当前屏幕可见区域，查找与 needle 图像匹配度 >= confidence 的区域，并点击匹配区域中心.
    定位image的时候，参考locate_img。

    confidence: [0, 1.0],
    duration: 移动鼠标时的速率
    check_interval: 以s的间隔去检查
    Raises: NeedleNotFoundException
    Reference:
    https://pyautogui.readthedocs.io/en/latest/screenshot.html#the-locate-functions

    """
    point = locate_img(needle_path, confidence, timeout, check_interval)
    click(point, duration)


def _is_img_onscreen(template_bgr: cv.Mat, confidence: float) -> Tuple[bool, Point]:
    """cv.TM_CCOEFF_NORMED 去matchTemplate"""
    _, w, h = template_bgr.shape[::-1]
    img = cv.cvtColor(_screenshot_ndarray(), cv.COLOR_RGB2BGR)

    result = cv.matchTemplate(img, template_bgr, cv.TM_CCOEFF_NORMED)
    match_indices = np.arange(result.size)[(result > confidence).flatten()]
    matches = np.unravel_index(match_indices[:1], result.shape)
    if len(matches[0]) == 0:
        return False, Point(-1, -1)
    matchx, matchy = matches[1], matches[0]
    points: List[Point] = []
    for x, y in zip(matchx, matchy):
        points.append(Point(x, y))
        points.append(Point(x + w, y + h))
    point = centroid(points)
    return True, point


def _load_pil_cv(file_path: Path) -> cv.Mat:
    """将以PIL.Image格式保存的文件读出并转换为cv格式"""
    with Image.open(file_path) as fp:
        img_array = np.array(fp)
    return cv.cvtColor(img_array, cv.COLOR_RGB2BGR)


def _wait_img_onscreen(
    needle_path: Path,
    confidence: float,
    timeout: int,
    check_interval: int,
) -> Point:
    """在指定时限内，等待直到指定图像出现在屏幕可见区域,返回中心坐标.
    Raises: NeedleNotFoundError"""
    end = time.time() + timeout
    found = False
    template = _load_pil_cv(needle_path)
    while time.time() < end and found is False:
        found, point = _is_img_onscreen(template, confidence)
        logger.info(f"wait for ({needle_path, confidence}) on screen: {found}")
        if found:
            return point
        time.sleep(check_interval)
    raise NeedleNotFoundError(f"wait for ({needle_path, confidence}) timeout")


def locate_img(
    needle_path: Path,
    confidence: float = 0.7,
    timeout: int = _DEFAULT_TIMEOUT,
    check_interval: int = _DEFAULT_CHECK_INTERVAL,
) -> Point:
    """在当前屏幕可见区域，查找与needle图像匹配度 >= confidence 的区域,返回中心点.
    通过cv.matchTemplate：method是用TM_CCOEFF_NORMED。
    适用于rotation, scale, and viewing angle恒定的情况
    Raises: NeedleNotFoundException"""
    point = _wait_img_onscreen(needle_path, confidence, timeout, check_interval)
    logger.info(f"locate {needle_path} with {confidence} at {point}")
    return point


def click_by_word(
    text: str,
    confidence: float = 0.7,
    timeout: int = _DEFAULT_TIMEOUT,
    duration: float = 0.4,
    ocr_config: str = "",
    preprocess: Optional[Callable[[cv.Mat], cv.Mat]] = None,
) -> None:
    """在当前屏幕可见区域查找单个单词（以空格分隔)，并点击.
    定位方法与规则见locate_word的参数说明
    Raises: NeedleNotFoundException"""
    point = locate_word(
        text, confidence, timeout, ocr_config=ocr_config, preprocess=preprocess
    )
    click(point, duration=duration)


def locate_word(
    text: str,
    confidence: float = 0.7,
    timeout: int = _DEFAULT_TIMEOUT,
    ocr_config: str = "",
    preprocess: Optional[Callable[[cv.Mat], cv.Mat]] = None,
    check_interval: int = _DEFAULT_CHECK_INTERVAL,
) -> Point:
    """在当前屏幕可见区域查找单个单词（以空格分隔),返回confidence最高的.
    匹配前会按preprocess做图像预处理
    preprocess:默认为空，即默认不做特殊处理.处理后的必须是opencv可识别的，
    opencv使用BGR而不是RGB，所以，如果原图是RGB，则需要使用
    cv.cvtColor(image, cv.COLOR_RGB2BGR)或者转换为GRAY。
    ocr_config:默认自动识别.用于调整psm，如果主要是文字，且默认识别不高时，可--psm 4 或者
    --psm 6,或者是 --psm 11
    check_interval: 以s间隔去检查屏幕
    Raises: NeedleNotFoundException"""
    boxes = _locate_word(
        text, confidence, timeout, ocr_config, preprocess, check_interval
    )
    top_lefts = [Point(box.left, box.top) for box in boxes]
    bottom_rights = [Point(box.left + box.width, box.top + box.height) for box in boxes]
    point = centroid(top_lefts + bottom_rights)
    logger.info(f"top match for {text}: {point}")
    return point


def print_enhance_ocr_tip() -> None:
    """Print out the tip how to enhance ocr accuracy."""
    logger.info(
        """Tips for improve the ocr accuracy:
    1. preprocess: 如果原图的图像颜色很丰富或者字样过浅，考虑先做color space转为gray，
    以及做按需调整threshold.
    如:Guacamole web login页面中，placeholder的颜色识别不出来，将threshold用THRESH_BINARY设置
    threshold为200.用def _img_preprocess(img):
        image = cv.cvtColor(img, cv.COLOR_RGB2GRAY)
        return cv.threshold(image, 200, 255, cv.THRESH_BINARY)[1]
    或者：调整threshold采用cv.adaptiveThreshold(
        img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2
    )
    2. 调整psm. 默认为3.可以按需设置为常用值4,6,11. 如ocr_config='--psm 4'"""
    )


def _locate_word(
    text: str,
    confidence: float,
    timeout: int,
    ocr_config: str,
    preprocess: Optional[Callable[[cv.Mat], cv.Mat]],
    check_interval: int,
) -> List[_TesseractMatchResult]:
    """在当前屏幕可见区域查找字串,返回confidence最高的.
    Raises:
    NeedleNotFoundException: 如果文字未出现或confidence不满足匹配条件"""
    img = _wait_word_onscreen(text, timeout, ocr_config, preprocess, check_interval)
    ocr_result = _ocr_result(img, ocr_config)
    ocr_result = _filter_ocr_result(ocr_result, text, confidence)
    word_block_nums = _ocr_same_row(ocr_result)
    top_match = _ocr_top_match(word_block_nums, ocr_result)
    return top_match


def _filter_ocr_result(
    result: Dict[str, Any], words: str, confidence: float
) -> Dict[str, List[_TesseractMatchResult]]:
    """从Tesseract返回的result中，过滤满足条件(包括字串以及满足confidence).
    Raises: NeedleNotFoundException"""
    # Tesseract返回的MatchResult 是用int百分来表示统一转换成百分率
    word_list = words.split()
    converted_confidence = min(int(confidence * 100), 100)
    results = collections.defaultdict(list)
    for text, block_num, conf, left, top, width, height in zip(
        result["text"],
        result["block_num"],
        result["conf"],
        result["left"],
        result["top"],
        result["width"],
        result["height"],
    ):
        # text in word_list : 当前单词是否在匹配列表中
        # words in text: 单个单词全匹配或者部分匹配
        if ((text in word_list) or (words in text)) and _validate_confidence(
            int(conf), converted_confidence, text
        ):
            results[text].append(
                _TesseractMatchResult(text, block_num, conf, left, top, width, height)
            )

    if len(results.keys()) < len(word_list):
        raise NeedleNotFoundError(f"no match for {text} with {confidence}: {results}")
    logger.info(f"matched result for {text} with {confidence}: {results}")
    # 转换成普通dict
    return dict(results)


def _validate_confidence(actual: float, expected: float, *args: Any) -> bool:
    """Check if confidence match."""
    if actual >= expected:
        logger.info(f"Confidence match {args}")
    else:
        logger.warning(f"Actual: {actual} expected: {expected}, {args}")
    return actual >= expected


def _ocr_same_row(matches: Dict[str, List[_TesseractMatchResult]]) -> List[int]:
    """找到所有单词的box的block_nums的交集.
    根据TessearctResult，(page_num,par_num,line_num,block_num)
    四元组，标识了单词属于同一行。
    这里不考虑pdf等多page的情况，故目前仅筛选block_num"""
    values = list(matches.values())
    first, others = values[0], values[1:]
    block_nums = set([result.block_num for result in first])
    for results in others:
        _block_nums = set([result.block_num for result in results])
        block_nums &= _block_nums
    return list(block_nums)


def _ocr_top_match(
    block_nums: List[int], matches: Dict[str, List[_TesseractMatchResult]]
) -> List[_TesseractMatchResult]:
    """根据block_nums，过滤满足条件confidence最高的的box data."""
    flatten_matches = [
        item
        for sublist in matches.values()
        for item in sublist
        if item.block_num in block_nums
    ]
    if len(block_nums) <= 1:
        return flatten_matches
    max_mean = -1
    for block_num in block_nums:
        avg = mean(m.confidence for m in flatten_matches if m.block_num == block_num)
        max_mean = max(max_mean, avg)
        if max_mean == avg:
            result = [m for m in flatten_matches if m.block_num == block_num]
    return result


def _ocr_result(image: cv.Mat, ocr_config: str) -> Any:
    """用pytesseract识别image的所有单词,返回识别出来的box boundary."""
    result = pytesseract.image_to_data(
        image, output_type=pytesseract.Output.DICT, config=ocr_config
    )
    return result


def _screenshot_ocr(preprocess: Optional[Callable[[cv.Mat], cv.Mat]]) -> cv.Mat:
    """截屏为pytesseract支持的格式,并根据preprocess做图像预处理.
    图像空间最后需为BGR或者GRAY，不能是RGB格式
    preprocess:默认为空，即默认不做特殊处理"""
    img = _screenshot_ndarray()
    if preprocess is None:
        # COLOR_RGB2GRAY or COLOR_RGB2BGR
        return cv.cvtColor(img, cv.COLOR_RGB2BGR)
    return preprocess(img)


def _is_word_onscreen(
    search: str,
    ocr_config: str,
    preprocess: Optional[Callable[[cv.Mat], cv.Mat]],
) -> Tuple[bool, cv.Mat]:
    """截图并根据preprocess函数对图像进行预处理，查找指定单词是否在屏幕可见区域.
    preprocess:默认为空，即默认不做特殊处理"""
    image = _screenshot_ocr(preprocess)
    result = pytesseract.image_to_string(image, config=ocr_config)
    logger.debug(f"is_word_onscreen {search}: {result}")
    return (search in result), image


def _wait_word_onscreen(
    search: str,
    timeout: int,
    ocr_config: str,
    preprocess: Optional[Callable[[cv.Mat], cv.Mat]],
    check_interval: int,
) -> cv.Mat:
    """在指定时限内，等待直到指定单词出现在屏幕可见区域.
    匹配前会根据preprocess对图像做预处理.
    preprocess:默认为空，即默认不做特殊处理
    return: processed image
    Raises: NeedleNotFoundError"""
    end = time.time() + timeout
    while time.time() < end:
        found, img = _is_word_onscreen(search, ocr_config, preprocess=preprocess)
        logger.info(f"wait for {search} on screen: {found}")
        if found:
            return img
        # 因为文字识别通过subprocess去调用Tesseract,不要过于频繁
        # Hardcode 为5
        time.sleep(check_interval)
    raise NeedleNotFoundError(f"wait for {search} timeout")
