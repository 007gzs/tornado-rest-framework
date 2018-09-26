######################
Tornado REST framework
######################
.. image:: https://travis-ci.org/007gzs/tornado-rest-framework.svg?branch=master
    :target: https://travis-ci.org/007gzs/tornado-rest-framework
.. image:: https://img.shields.io/pypi/v/tornadoapi.svg
    :target: https://pypi.org/project/tornadoapi

Tornado REST framework
`【阅读文档】 <http://tornadoapi.readthedocs.io/zh_CN/latest/>`_。

安装
---------------------
目前 tornadoapi 支持的 Python 环境有 2.7, 3.4, 3.5, 3.6 和 pypy。::

    pip install tornadoapi

快速开始
_____________________

启动之前或启动脚本开始时配置环境变量::

    os.environ.setdefault("TORNADOAPI_SETTINGS_MODULE", "config.settings")

config/settings.py 中增加自定义配置::

    DEBUG = True
    TEST = 1

通过以下代码可以获取到settings参数::

    from tornadoapi.conf import settings

    settings.TEST

ApiHandler调用示例::

    from tornadoapi.handler import ApiHandler

    class TestHandler(ApiHandler):
        test_param = fields.CharField(description='测试参数', default=None)
        test_choice = fields.ChoiceField(description='选择参数', default=None, choices=((0, '选项0'), (1, '选项1')))

        @classmethod
        def get_return_sample(cls):
            return ErrCode.SUCCESS.get_res_dict(data={'test_param': '测试参数', 'test_choice' :'选择参数'})

        @classmethod
        def get_handler_name(cls):
            return '测试'

        def get(self, *args, **kwargs):
            ret = {
                'test_param': self.test_param,
                'test_choice': self.test_choice
            }
            self.write_api(ret)
示例项目
---------------------

`demo <https://github.com/007gzs/tornadoapi-example/>`_
