# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import time

from tornadoapi.storage import BaseStorage


class MemoryStorage(BaseStorage):

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        ret = self._data.get(key, None)
        if ret is None or len(ret) != 2:
            return default
        else:
            value = ret[0]
            expires_at = ret[1]
            if expires_at is None or expires_at > time.time():
                return value
            else:
                return default

    def set(self, key, value, ttl=None):
        if value is None:
            return
        if ttl is not None:
            ttl = int(time.time()) + ttl
        self._data[key] = (value, ttl)

    def delete(self, key):
        self._data.pop(key, None)
