Handler
===========================================

.. module:: tornadoapi.handler

.. autoclass:: ApiHandler
   :members:
   :inherited-members:

`ApiHandler` 基本使用方法::

   from tornadoapi import handler, fields

   class MyHandler(handler.ApiHandler):
       test_param = fields.CharField()
       def get(self, *args, **kwargs):
           self.write_api(self.test_param)


.. toctree::
   :maxdepth: 2
   :glob:

   fields/*
