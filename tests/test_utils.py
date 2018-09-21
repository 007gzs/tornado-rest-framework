# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest

from tornadoapi.core import ObjectDict


class UtilityTestCase(unittest.TestCase):

    def test_object_dict(self):
        obj = ObjectDict()
        self.assertTrue(obj.xxx is None)
        self.assertTrue(obj['xxx'] is None)
        obj.xxx = 1
        self.assertEqual(1, obj.xxx)
        self.assertEqual(obj['xxx'], obj.xxx)
