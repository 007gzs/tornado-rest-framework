# encoding: utf-8
from __future__ import absolute_import, unicode_literals

__version__ = '1.1.0'
__author__ = '007gzs'


def setup():
    """
    Configure the settings (this happens as a side effect of accessing the first setting), configure logging.
    """
    from tornadoapi.conf import settings
    from tornadoapi.core.log import configure_logging

    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
