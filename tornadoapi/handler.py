# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import json
from collections import OrderedDict

import six
from tornado import web
from tornado.routing import PathMatches
from tornado.web import HTTPError
from tornadoapi.core import logger_handler, to_text, logger

from tornadoapi.core.code import CodeData
from tornadoapi.core.err_code import ErrCode
from tornadoapi.core.exceptions import CustomError, ValidationError
from tornadoapi.core.traceback import ExceptionReporter
from tornadoapi.fields import Field, empty
from tornadoapi.template import get_resource_template_html
from tornadoapi.template.jinja2_loader import Jinja2TemplateLoader


class BaseHandler(web.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.__tonadoapi_prepare_user = self.prepare
        self.prepare = self.tonadoapi_prepare

    @classmethod
    def get_handler_name(cls):
        """
        重写返回接口名称
        """
        return cls.__name__

    @classmethod
    def get_handler_description(cls):
        """
        重写返回接口描述
        """
        return ''

    @classmethod
    def get_handler_remark(cls):
        """
        重写返回接口备注
        """
        return ''

    def tonadoapi_prepare(self):
        self.__tonadoapi_prepare_user()

    def data_received(self, chunk):
        pass

    def mail_exc_info(self, exc_info):
        logger.error(
            'Internal Server Error: %s', self.request.uri,
            exc_info=exc_info,
            extra={'status_code': 500, 'handler': self},
        )

    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs:
            if isinstance(kwargs['exc_info'][1], HTTPError):
                kwargs.pop('exc_info')
            else:
                if self.settings.get("serve_traceback"):
                    is_html = self.request.headers.get('X-Requested-With') != 'XMLHttpRequest'
                    reporter = ExceptionReporter(self, *kwargs['exc_info'])
                    res_data = reporter.get_traceback_html() if is_html else reporter.get_traceback_text()
                    if is_html:
                        self.set_header("Content-Type", "text/html; charset=UTF-8")
                    else:
                        self.set_header("Content-Type", "text/plant; charset=UTF-8")
                    self.finish(res_data)
                    return
                else:
                    self.mail_exc_info(kwargs['exc_info'])

        super(BaseHandler, self).write_error(status_code, **kwargs)

    def head(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def set_default_headers(self):
        headers = self.settings.get('headers', {})

        # Allow for overriding headers
        for header_name, value in headers.items():
            try:
                self.set_header(header_name, value)
            except Exception as e:
                # tornado raise Exception (not a subclass)
                # if method is unsupported (websocket and Access-Control-Allow-Origin
                # for example, so just ignore)
                self.log.debug(e)

    @classmethod
    def support_methods(cls):
        ret = list()
        for method_key in cls.SUPPORTED_METHODS:
            if getattr(cls, method_key.lower()) != getattr(BaseHandler, method_key.lower()):
                ret.append(method_key)
        if 'GET' in ret and 'HEAD' not in ret:
            ret.append('HEAD')
        return ret

    @property
    def debug(self):
        return self.settings.get('debug')

    @property
    def log(self):
        return logger_handler


class Jinja2TemplateHandler(BaseHandler):
    def create_template_loader(self, template_path):
        return Jinja2TemplateLoader(template_path)


API_FORMAT_JSON = 'json'
API_FORMAT_JSONP = 'jsonp'
API_FORMAT_PREVIEW = 'preview'


class ApiHandler(BaseHandler):
    CUSTOM_ERROR_STATUS_CODE = 400
    EXCEPTION_STATUS_CODE = 500

    @classmethod
    def tonadoapi_get_class_name(cls):
        return '{}.{}'.format(cls.__module__, cls.__name__)

    @classmethod
    def tonadoapi_field_info(cls):
        if hasattr(cls, '__tonadoapi_field_info') \
                and hasattr(cls, '__tonadoapi_class_name') \
                and cls.tonadoapi_get_class_name() == getattr(cls, '__tonadoapi_class_name'):
            return getattr(cls, '__tonadoapi_field_info')
        field_info = OrderedDict()
        for field_name in dir(cls):
            field = getattr(cls, field_name, None)
            if not isinstance(field, Field):
                continue
            field_info[field_name] = field.get_field_info()
        setattr(cls, '__tonadoapi_field_info', field_info)
        setattr(cls, '__tonadoapi_field_info', cls.tonadoapi_get_class_name())
        return field_info

    def tonadoapi_prepare(self):
        self.tonadoapi_field_info()
        super(ApiHandler, self).tonadoapi_prepare()
        errors = {}
        for field_name in dir(self):
            field = getattr(self, field_name, None)
            if not isinstance(field, Field):
                continue
            if field.raw_body:
                if self.request.method.upper() in ('HEAD', 'GET', 'OPTIONS'):
                    data = empty
                else:
                    data = to_text(self.request.body)
            else:
                data = self.path_kwargs.get(field_name, self.get_argument(field_name, empty))
            try:
                value = field.run_validation(data)
            except ValidationError as exc:
                if isinstance(exc.detail, dict):
                    raise
                errors[field_name] = exc.detail
            else:
                setattr(self, field_name, value)
        if errors:
            raise CustomError(ErrCode.ERR_COMMON_BAD_PARAM, data=errors)

    @classmethod
    def get_return_sample(cls):
        return ''

    def get_format(self, params_name="format"):
        _format = self.get_argument(params_name, None)
        if not _format:
            xhr = self.request.headers.get('X-Requested-With')
            if xhr == 'XMLHttpRequest':
                _format = API_FORMAT_JSON
            else:
                accept = self.request.headers.get('Accept')
                if accept:
                    if 'javascript' in accept.lower():
                        _format = API_FORMAT_JSONP
                    elif 'json' in accept.lower():
                        _format = API_FORMAT_JSON
        else:
            _format = _format.lower()
        return _format or (API_FORMAT_PREVIEW if self.debug else API_FORMAT_JSON)

    def write_api(self, obj, no_fail=False, fmt=None, **kwargs):
        if isinstance(obj, (CustomError, CodeData)):
            obj = obj.get_res_dict()
        elif not isinstance(obj, dict) or 'code' not in obj:
            obj = ErrCode.SUCCESS.get_res_dict(data=obj)
        if not fmt:
            fmt = self.get_format()
        support_format = (API_FORMAT_JSON, API_FORMAT_JSONP, API_FORMAT_PREVIEW)
        if not self.debug:
            support_format = (API_FORMAT_JSON, API_FORMAT_JSONP)

        if fmt not in support_format and no_fail:
            fmt = API_FORMAT_JSON
        if fmt == API_FORMAT_PREVIEW and self.debug:
            html = get_resource_template_html(
                'apiview.html',
                namespace=self.get_template_namespace(),
                res_data=obj,
                field_info=self.tonadoapi_field_info(),
                handler_name=self.get_handler_name(),
                url=self.request.uri,
                method=self.request.method,
                return_sample=self.get_return_sample(),
                description=self.get_handler_description(),
                remark=self.get_handler_remark(),
                support_methods=self.support_methods()
            )
            self.set_header("Content-Type", "text/html; charset=UTF-8")
            self.finish(html)
        elif fmt == API_FORMAT_JSON:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.finish(json.dumps(obj))
        elif fmt == API_FORMAT_JSONP:
            self.set_header("Content-Type", "application/javascript")
            callback = self.get_argument('callback', 'callback')
            self.finish('%s(%s);' % (callback, json.dumps(obj)))
        else:
            self.log.error("format error %s" % fmt)
            raise CustomError(ErrCode.ERR_COMMON_BAD_PARAM)

    def log_exception(self, typ, value, tb):
        if isinstance(value, CustomError):
            return
        else:
            if not isinstance(value, HTTPError):
                self.log.error("ApiHandler exception %s\n%r", self._request_summary(),
                               self.request, exc_info=(typ, value, tb))
            super(ApiHandler, self).log_exception(typ, value, tb)

    def send_error(self, status_code=500, **kwargs):
        if 'exc_info' in kwargs:
            exc_info = kwargs['exc_info']
            if self._finished:
                self.log.error("ApiHandler exception in finished %s\n%r", self._request_summary(),
                               self.request, exc_info=exc_info)
            else:
                if isinstance(exc_info[1], CustomError):
                    kwargs['__api_data'] = exc_info[1]
                    status_code = exc_info[1].status_code
                    if status_code is not None:
                        if not isinstance(status_code, six.integer_types):
                            status_code = to_text(status_code)
                            if not status_code.isdigit():
                                status_code = None
                            else:
                                status_code = int(status_code)

                    if status_code is None or status_code <= 0 or status_code >= 1000:
                        status_code = self.CUSTOM_ERROR_STATUS_CODE
                else:
                    kwargs['__api_data'] = ErrCode.ERR_SYS_ERROR
                    kwargs['__api_exc_info'] = exc_info
                    if not isinstance(exc_info[1], HTTPError):
                        status_code = self.EXCEPTION_STATUS_CODE
                        self.mail_exc_info(exc_info)
        super(ApiHandler, self).send_error(status_code, **kwargs)

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        if '__api_data' in kwargs and isinstance(kwargs['__api_data'], (CustomError, CodeData)):
            self.write_api(kwargs['__api_data'], True)
        else:
            super(ApiHandler, self).write_error(status_code, **kwargs)


class NotFoundHandler(BaseHandler):
    def prepare(self):
        raise web.HTTPError(404)


class ApiDocHandler(BaseHandler):

    def get(self, *args, **kwargs):
        api_list = list()
        for rule in self.application.wildcard_router.rules:
            if not issubclass(rule.target, ApiHandler):
                continue
            data = {
                'class_name': rule.target.tonadoapi_get_class_name(),
                'name': rule.name or rule.target.get_handler_name(),
                'path': rule.matcher.regex.pattern[:-1] if isinstance(rule.matcher, PathMatches) else str(rule.matcher),
                'support_methods': rule.target.support_methods(),
                'field_info': rule.target.tonadoapi_field_info(),
                'return_sample': rule.target.get_return_sample()
            }
            api_list.append(data)
        ret_sample = {'code': '错误码', 'message': '错误描述', 'data': '数据'}
        html = get_resource_template_html(
            'doc.html',
            namespace=self.get_template_namespace(),
            err_codes=[getattr(ErrCode, tag) for tag in ErrCode.get_tags()],
            ret_sample_data=ret_sample,
            api_list=api_list,
        )
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.finish(html)
