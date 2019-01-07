# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest


class StorageTestCase(unittest.TestCase):

    def test_caches(self, storage=None):
        if storage is None:
            return
        from tornadoapi.storage.cache import SampleCache
        if storage is None:
            return
        cache = SampleCache(storage)
        cache.test_item1.set('key', 'test1', 7200)
        cache.test_item2.set('key', 'test2', 7200)

    def test_memory_storage(self):
        from tornadoapi.storage.memorystorage import MemoryStorage

        storage = MemoryStorage()
        self.test_caches(storage)

    def test_redis_storage(self):
        from redis import Redis
        from tornadoapi.storage.kvstorage import KvStorage
        redis = Redis()
        storage = KvStorage(redis)
        self.test_caches(storage)

    def test_memcache_storage(self):
        from pymemcache.client import Client
        from tornadoapi.storage.kvstorage import KvStorage
        servers = ("127.0.0.1", 11211)
        memcached = Client(servers)
        storage = KvStorage(memcached)
        self.test_caches(storage)
