# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import decimal
import json
import logging
import random
import string
import uuid
from pprint import pformat

import six

logger = logging.getLogger('tornadoapi')
logger_handler = logging.getLogger('tornadoapi.handler')


class ObjectDict(dict):
    """Makes a dictionary behave like an object, with attribute-style access.
    """

    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None

    def __setattr__(self, key, value):
        self[key] = value


def to_text(value, encoding='utf-8'):
    """Convert value to unicode, default encoding is utf-8

    :param value: Value to be converted
    :param encoding: Desired encoding
    """
    if not value:
        return ''
    if isinstance(value, six.text_type):
        return value
    if isinstance(value, six.binary_type):
        return value.decode(encoding)
    return six.text_type(value)


def to_binary(value, encoding='utf-8'):
    """Convert value to binary string, default encoding is utf-8

    :param value: Value to be converted
    :param encoding: Desired encoding
    """
    if not value:
        return b''
    if isinstance(value, six.binary_type):
        return value
    if isinstance(value, six.text_type):
        return value.encode(encoding)
    return to_text(value).encode(encoding)


def random_string(length=16):
    rule = string.ascii_letters + string.digits
    rand_list = random.sample(rule, length)
    return ''.join(rand_list)


def byte2int(c):
    if six.PY2:
        return ord(c)
    return c


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        from tornadoapi.conf import settings
        if isinstance(o, datetime.datetime):
            return o.strftime(settings.SHORT_DATETIME_FORMAT)
        elif isinstance(o, datetime.date):
            return o.strftime(settings.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(settings.TIME_FORMAT)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, uuid.UUID):
            return str(o)
        else:
            return super(JSONEncoder, self).default(o)


def json_dumps(obj, indent=None, cls=JSONEncoder, **kwargs):
    return json.dumps(obj, indent=indent, cls=cls, **kwargs)


def json_loads(s, object_hook=ObjectDict, **kwargs):
    return json.loads(s, object_hook=object_hook, **kwargs)


def url_path_join(*pieces):
    """Join components of url into a relative url

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    initial = pieces[0].startswith('/')
    final = pieces[-1].endswith('/')
    stripped = [s.strip('/') for s in pieces]
    result = '/'.join(s for s in stripped if s)
    if initial:
        result = '/' + result
    if final:
        result = result + '/'
    if result == '//':
        result = '/'
    return result


def escape(s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;")  # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s


def pprint(value):
    """A wrapper around pprint.pprint -- for debugging, really."""
    try:
        return pformat(value)
    except Exception as e:
        return "Error in formatting: %s: %s" % (e.__class__.__name__, e)


if six.PY3:
    to_str = to_text
else:
    to_str = to_binary
