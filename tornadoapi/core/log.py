# encoding: utf-8
from __future__ import absolute_import, unicode_literals
from __future__ import unicode_literals

import logging
import logging.config  # needed when logging_config doesn't start with logging.config


# Default logging for tornadoapi. This sends an email to the site admins on every
# HTTP 500 error. Depending on DEBUG, all other log records are either sent to
# the console (DEBUG=True) or discarded (DEBUG=False) by means of the
# require_debug_true filter.
from tornadoapi.conf import settings
from tornadoapi.core.module_loading import import_string

DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'tornadoapi.core.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'tornadoapi.core.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s %(filename)s(%(lineno)d) %(levelname)s %(process)d %(message)s',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'tornadoapi.handler': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        }
    },
    'loggers': {
        'tornado.access': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'tornado.application': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'tornado.general': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'tornadoapi': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'tornadoapi.handler': {
            'handlers': ['tornadoapi.handler'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}


def configure_logging(logging_config, logging_settings):
    logging.config.dictConfig(DEFAULT_LOGGING)
    if logging_config:
        # First find the logging configuration function ...
        logging_config_func = import_string(logging_config)

        # ... then invoke it with the logging settings
        if logging_settings:
            logging_config_func(logging_settings)


class RequireDebugFalse(logging.Filter):
    def filter(self, record):
        return not settings.DEBUG


class RequireDebugTrue(logging.Filter):
    def filter(self, record):
        return settings.DEBUG
