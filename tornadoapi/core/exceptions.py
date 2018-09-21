# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import six
from tornadoapi.core import to_text, to_binary

from tornadoapi.core.err_code import ErrCode


class CustomError(ValueError):
    """
    客户操作错误，用于在系统流程设计不完善时，处理客户无意提交的错误请求
    """
    def __init__(self, errcode=ErrCode.ERR_COMMON_BAD_PARAM, **kwargs):
        self.code = errcode
        self.kwargs = kwargs
        self.message = self.kwargs.get('message', errcode.message)
        super(CustomError, self).__init__(self.message)

    def get_res_dict(self):
        return self.code.get_res_dict(**self.kwargs)


class ErrorDetail(six.text_type):
    """
    A string-like object that can additionally have a code.
    """
    code = None

    def __new__(cls, string, code=None):
        self = super(ErrorDetail, cls).__new__(cls, string)
        self.code = code
        return self

    def __eq__(self, other):
        r = super(ErrorDetail, self).__eq__(other)
        try:
            return r and self.code == other.code
        except AttributeError:
            return r

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return to_binary('ErrorDetail(string=%r, code=%r)' % (
            six.text_type(self),
            self.code,
        ))

    def __hash__(self):
        return hash(str(self))


def _get_error_details(data, default_code=None):
    """
    Descend into a nested data structure, forcing any
    lazy translation strings or strings into `ErrorDetail`.
    """
    if isinstance(data, list):
        ret = [
            _get_error_details(item, default_code) for item in data
        ]
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, default_code)
            for key, value in data.items()
        }
        return ret

    text = to_text(data)
    code = getattr(data, 'code', default_code)
    return ErrorDetail(text, code)


class ValidationError(Exception):
    default_detail = 'Invalid input.'
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)
