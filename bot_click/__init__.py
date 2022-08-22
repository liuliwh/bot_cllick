"""The core lib to provide bot click, including ocr, image recognition and mixins."""
import logging

# Set default logging handler to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

from .bot_click import *
from .mixins import *
