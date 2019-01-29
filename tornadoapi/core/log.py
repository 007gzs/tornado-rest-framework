# encoding: utf-8
from __future__ import absolute_import, unicode_literals
from __future__ import unicode_literals

import logging
import logging.config  # needed when logging_config doesn't start with logging.config


# Default logging for tornadoapi. This sends an email to the site admins on every
# HTTP 500 error. Depending on DEBUG, all other log records are either sent to
# the console (DEBUG=True) or discarded (DEBUG=False) by means of the
# require_debug_true filter.
from copy import copy

from tornadoapi.core import mail
from tornadoapi.core.traceback import ExceptionReporter

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
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'tornadoapi.core.log.AdminEmailHandler',
            'include_html': True
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
            'handlers': ['console', 'mail_admins'],
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


class AdminEmailHandler(logging.Handler):
    """An exception log handler that emails log entries to site admins.
    If the request is passed as the first argument to the log record,
    request data will be provided in the email report.
    """

    def __init__(self, include_html=False):
        super(AdminEmailHandler, self).__init__()
        self.include_html = include_html

    def emit(self, record):
        subject = '%s: %s' % (
            record.levelname,
            record.getMessage()
        )
        subject = self.format_subject(subject)

        # Since we add a nicely formatted traceback on our own, create a copy
        # of the log record without the exception data.
        no_exc_record = copy(record)
        no_exc_record.exc_info = None
        no_exc_record.exc_text = None

        if record.exc_info:
            exc_info = record.exc_info
        else:
            exc_info = (None, record.getMessage(), None)

        reporter = ExceptionReporter(getattr(record, 'handler', None), *exc_info, is_email=True)
        message = "%s\n\n%s" % (self.format(no_exc_record), reporter.get_traceback_text())
        html_message = reporter.get_traceback_html() if self.include_html else None
        self.send_mail(subject, message, fail_silently=True, html_message=html_message)

    def send_mail(self, subject, message, *args, **kwargs):
        mail.mail_admins(subject, message, *args, **kwargs)

    def format_subject(self, subject):
        """
        Escape CR and LF characters.
        """
        return subject.replace('\n', '\\n').replace('\r', '\\r')
