# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import six

from tornadoapi.conf import settings
from tornadoapi.core import to_text


class CodeData(object):

    def __init__(self, code, tag, message):
        self.code = code
        self.message = message
        self.tag = tag

    def __str__(self):
        return str(self.code)

    def __eq__(self, other):
        if isinstance(other, CodeData):
            return other.code == self.code
        elif isinstance(other, type(self.code)):
            return other == self.code
        else:
            return super(CodeData, self).__eq__(other)

    @classmethod
    def get_code_tag(cls):
        code_tag = 'code'
        if settings.RESPONSE_CODE_TAG and isinstance(settings.RESPONSE_CODE_TAG, six.string_types):
            code_tag = to_text(settings.RESPONSE_CODE_TAG)
        return code_tag

    @classmethod
    def get_message_tag(cls):
        message_tag = 'message'
        if settings.RESPONSE_MESSAGE_TAG and isinstance(settings.RESPONSE_MESSAGE_TAG, six.string_types):
            message_tag = to_text(settings.RESPONSE_MESSAGE_TAG)
        return message_tag

    @classmethod
    def get_data_tag(cls):
        data_tag = 'data'
        if settings.RESPONSE_DATA_TAG and isinstance(settings.RESPONSE_DATA_TAG, six.string_types):
            data_tag = to_text(settings.RESPONSE_DATA_TAG)
        return data_tag

    def get_res_dict(self, **kwargs):
        ret = dict(kwargs)
        code_tag = self.get_code_tag()
        message_tag = self.get_message_tag()
        ret[code_tag] = self.code
        if message_tag not in ret:
            ret[message_tag] = self.message
        return ret


class Code(object):

    def __init__(self, code_define):
        codes = set()
        self._list = list()
        self._dict = dict()
        self._tags = list()
        for tag, code, message in code_define:
            assert code not in codes and not hasattr(self, tag)
            setattr(self, tag, CodeData(code, tag, message))
            codes.add(code)
            self._tags.append(tag)
            self._list.append((code, message))
            self._dict[code] = message

    def get_list(self):
        return self._list

    def get_dict(self):
        return self._dict

    def get_tags(self):
        return self._tags
