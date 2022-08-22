import logging

# Set default logging handler to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

from .guacamole import GuacaLoginScreen
from .windows import AbstractWindowsBrowserScreen as WindowsBrowserScreen
