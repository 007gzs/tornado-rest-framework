快速开始
==========

启动之前或启动脚本开始时配置环境变量 并执行setup初始化::

    os.environ.setdefault("TORNADOAPI_SETTINGS_MODULE", "config.settings")
    import tornadoapi
    tornadoapi.setup()

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
