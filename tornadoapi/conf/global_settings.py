# encoding: utf-8
from __future__ import absolute_import, unicode_literals

DEBUG = False
# Default formatting for date objects. See all available format strings here:
DATE_FORMAT = '%Y-%m-%d'

# Default formatting for datetime objects. See all available format strings here:
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

# Default formatting for time objects. See all available format strings here:
TIME_FORMAT = '%H:%M:%S'

# Default formatting for date objects when only the year and month are relevant.
# See all available format strings here:
YEAR_MONTH_FORMAT = '%Y-%m'

# Default formatting for date objects when only the month and day are relevant.
# See all available format strings here:
MONTH_DAY_FORMAT = '%m-%d'

# Default short formatting for date objects. See all available format strings here:
SHORT_DATE_FORMAT = '%m/%d/%y'

# Default short formatting for datetime objects.
# See all available format strings here:
SHORT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Default formats to be used when parsing dates from input boxes, in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
DATE_INPUT_FORMATS = [
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',  # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',             # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',             # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',             # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',             # '25 October 2006', '25 October, 2006'
]

# Default formats to be used when parsing times from input boxes, in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
TIME_INPUT_FORMATS = [
    '%H:%M:%S',     # '14:30:59'
    '%H:%M:%S.%f',  # '14:30:59.000200'
    '%H:%M',        # '14:30'
]

# Default formats to be used when parsing dates and times from input boxes,
# in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
DATETIME_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M:%S.%f',  # '2006-10-25 14:30:59.000200'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M:%S.%f',  # '10/25/2006 14:30:59.000200'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M:%S.%f',  # '10/25/06 14:30:59.000200'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
]

TEMPLATE_CONFIG = {
    'cache_directory': '_template_cache'
}

# response code and message tag
RESPONSE_CODE_TAG = 'code'
RESPONSE_MESSAGE_TAG = 'message'
RESPONSE_DATA_TAG = 'data'

# The callable to use to configure logging
LOGGING_CONFIG = 'logging.config.dictConfig'

# Custom logging configuration.
LOGGING = {}

# People who get code error notifications.
# In the format [('Full Name', 'email@example.com'), ('Full Name', 'anotheremail@example.com')]
ADMINS = []

# Not-necessarily-technical managers of the site. They get broken link
# notifications and other various emails.
MANAGERS = ADMINS

# Default email address to use for various automated correspondence from
# the site managers.
DEFAULT_FROM_EMAIL = 'webmaster@localhost'

# Subject-line prefix for email messages send with tornadoapi.core.mail.mail_admins
# or ...mail_managers.  Make sure to include the trailing space.
EMAIL_SUBJECT_PREFIX = '[Tornado Api]'

# Email address that error messages come from.
SERVER_EMAIL = 'root@localhost'
DEFAULT_CHARSET = 'utf-8'

# The email backend to use. For possible shortcuts see django.core.mail.
# The default is to use the SMTP backend.
# Third-party backends can be specified by providing a Python path
# to a module that defines an EmailBackend class.
EMAIL_BACKEND = 'tornadoapi.core.mail.backends.smtp.EmailBackend'

# Host for sending email.
EMAIL_HOST = 'localhost'

# Port for sending email.
EMAIL_PORT = 25

# Whether to send SMTP 'Date' header in the local time zone or in UTC.
EMAIL_USE_LOCALTIME = False

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_SSL_CERTFILE = None
EMAIL_SSL_KEYFILE = None
EMAIL_TIMEOUT = None
