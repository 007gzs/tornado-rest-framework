# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import json
from collections import OrderedDict

import six
from tornado import web
from tornado.routing import PathMatches
from tornado.web import HTTPError
from tornadoapi.core import escape, logger_handler

from tornadoapi.core.code import CodeData
from tornadoapi.core.err_code import ErrCode
from tornadoapi.core.exceptions import CustomError, ValidationError
from tornadoapi.fields import Field, empty


def get_field_info_table_html(field_info):
    field_info_html = ""
    if field_info:
        show_keys = ('description', 'type', 'default', 'help_text', 'ex_info')
        field_info_html += '<table class="params panel">\n'
        field_info_html += '<tr><th>参数</th><th>名称</th><th>类型</th><th>默认值</th><th>说明</th><th>限制</th></tr>'
        for name, info in field_info.items():
            field_info_html += "<tr>"
            style = []
            if info['raw_body']:
                style.append('raw_body')
            if info['required']:
                name = "*{}*".format(name)
                style.append('required')
            else:
                name = "[{}]".format(name)
            field_info_html += "<td class='{}'>{}</td>".format(' '.join(style), name)
            for key in show_keys:
                field_info_html += "<td>{}</td>".format(escape(six.text_type(info.get(key, ''))))
            field_info_html += "</tr>\n"
        field_info_html += "</table>\n"
    return field_info_html


class BaseHandler(web.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.__tonadoapi_prepare_user = self.prepare
        self.prepare = self.tonadoapi_prepare

    @classmethod
    def get_handler_name(cls):
        return cls.__name__

    def tonadoapi_prepare(self):
        self.__tonadoapi_prepare_user()

    def data_received(self, chunk):
        pass

    def write_error(self, status_code, **kwargs):
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            if isinstance(kwargs['exc_info'][1], HTTPError):
                kwargs.pop('exc_info')
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
                data = self.request.body
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

    def get_preview_html(self, obj, field_info):

        res_data = json.dumps(obj, ensure_ascii=False, indent=4)
        field_info_html = get_field_info_table_html(field_info)
        if field_info_html:
            field_info_html = "<span class='title'>参数列表</span>" + field_info_html
        return_sample = self.get_return_sample()
        return_sample_html = ''
        if return_sample:
            ret_sample_data = json.dumps(return_sample, ensure_ascii=False, indent=4)
            return_sample_html = """
    <div class='api panel'>
    <span class='title'>返回格式说明</span>
    <div class="panel res_data bg">
    <pre>{ret_sample_data}</pre>
    </div>
""".format(ret_sample_data=ret_sample_data)
        style = """
<style>
body{ margin: 0; padding: 0; font-size:16px}
body,html{-webkit-text-size-adjust: none;width: 100%;height: 100%;}
*{text-decoration: none;list-style: none;}
img{border: 0px;}
table,table tr th, table tr td { border:1px solid #000000; }
table{background: #cccccc; min-height: 25px; line-height: 25px; text-align: center; border-collapse: collapse;}
.raw_body {font-style: italic;}
#content{ width: 90%; margin-left: 5%}
#res_data{ max-width: 100%; overflow-x: auto; }
.bg { background: #cccccc; margin: 0; border-radius: 10px }
pre {padding: 10px}
.panel { width: 100%; margin-bottom:10px}

</style>
        """
        html = """
<html>
<head>
<meta name="viewport" content="width=device-width,minimum-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>{name}</title>
{style}
</head>
<body>
<div id="content">
<h3>{name}</h3>

<span class='title'>请求地址</span>
<div class="panel bg">
<pre>{method} {url}</pre>
</div>
<span class='title'>支持请求类型</span>
<div class="panel bg">
<pre>{support_methods}</pre>
</div>
{field_info_html}
<span class='title'>返回结果</span>
<div id="res_data" class="panel bg">
<pre>
{res_data}
</pre>
</div>
{return_sample_html}
</div>
</body>
</heml>
""".format(
            name=self.get_handler_name(),
            res_data=escape(res_data),
            field_info_html=field_info_html,
            style=style,
            url=self.request.uri,
            method=self.request.method,
            return_sample_html=return_sample_html,
            support_methods=' '.join(self.support_methods()))
        return html

    def write_api(self, obj, no_fail=False, fmt=None, **kwargs):
        if not obj:
            obj = {}
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
            html = self.get_preview_html(obj, self.tonadoapi_field_info())
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
                    status_code = self.CUSTOM_ERROR_STATUS_CODE
                else:
                    kwargs['__api_data'] = ErrCode.ERR_SYS_ERROR
                    kwargs['__api_exc_info'] = exc_info
                    if not isinstance(exc_info[1], HTTPError):
                        status_code = self.EXCEPTION_STATUS_CODE
        super(ApiHandler, self).send_error(status_code, **kwargs)

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        if '__api_data' in kwargs and isinstance(kwargs['__api_data'], (CustomError, CodeData)):
            self.write_api(kwargs['__api_data'], True, exc_info=kwargs.get('__api_exc_info'))
        else:
            super(ApiHandler, self).write_error(status_code, **kwargs)


class NotFoundHandler(BaseHandler):
    def prepare(self):
        raise web.HTTPError(404)


class ApiDocHandler(BaseHandler):

    def get_doc_html(self, api_list):
        errcode_html = ""
        for tag in ErrCode.get_tags():
            code_data = getattr(ErrCode, tag)
            errcode_html += "{tag} = {code}; // {message} \n".format(
                tag=code_data.tag, code=code_data.code, message=code_data.message)
        content = ""
        menu = ""
        index = 0
        for api in api_list:
            index += 1
            field_info_html = get_field_info_table_html(api['field_info'])
            if field_info_html:
                field_info_html = "<span class='title'>参数列表</span>" + field_info_html
            return_sample = ''
            if api['return_sample']:
                ret_sample_data = json.dumps(api['return_sample'], ensure_ascii=False, indent=4)
                return_sample = """
<div class='api panel'>
<span class='title'>返回格式说明</span>
<div class="panel res_data bg">
<pre>{ret_sample_data}</pre>
</div>
""".format(ret_sample_data=ret_sample_data)
            menu += "<li><a href='#api_{index}'>{name}</a></li>\n".format(name=api['name'], index=index)
            content += """
<div class='api panel'>
<a name='api_{index}'></a>
<h3>{name}</h3>
<span class='title'>请求地址</span>
<div class="panel bg">
<pre>{path}</pre>
</div>
<span class='title'>支持请求类型</span>
<div class="panel bg">
<pre>{support_methods}</pre>
</div>
{field_info_html}
{return_sample}
</div>
""".format(
                path=escape(api['path']),
                name=api['name'],
                support_methods=' '.join(api['support_methods']),
                field_info_html=field_info_html,
                return_sample=return_sample,
                index=index
            )
        style = """
<style>
body{ margin: 0; padding: 0; font-size:16px}
body,html{-webkit-text-size-adjust: none;width: 100%;height: 100%;}
*{text-decoration: none;list-style: none;}
a:link {color: #000; text-decoration: none;}
a:visited {text-decoration: none; color: #000;}
a:hover {text-decoration: underline;color: #000;}
a:active {text-decoration: none;}
img{border: 0px;}
table,table tr th, table tr td { border:1px solid #000000; }
table{background: #cccccc; min-height: 25px; line-height: 25px; text-align: center; border-collapse: collapse;}
.raw_body {font-style: italic;}
#content{ width: 90%; margin-left: 5%}
div.res_data{ max-width: 100%; overflow-x: auto; }
div.api {clear: both; margin-bottom:50px}
pre {padding: 10px}
.bg { background: #cccccc; margin: 0; border-radius: 10px }
.panel { width: 100%; margin-bottom:5px}
li {margin:5px 50px}
</style>
"""
        ret_sample = {'code': '错误码', 'message': '错误描述', 'data': '数据'}
        ret_sample_data = json.dumps(ret_sample, ensure_ascii=False, indent=4)
        html = """
<html>
<head>
<meta name="viewport" content="width=device-width,minimum-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>接口列表</title>
{style}
</head>
<body>
<div id="content">
    <a name='api_0'></a>
    <div class='api panel'>
        <span class='title'>错误码</span>
        <div class="panel bg">
        <pre>{errcode}</pre>
        </div>
    </div>
    <div class='api panel'>
        <span class='title'>返回格式</span>
        <div class="panel res_data bg">
        <pre>{ret_sample_data}</pre>
        </div>
    </div>
    <div class='api panel'>
        <span class='title'>接口列表</span>
        <div class="panel">
        {menu}
        </div>
    </div>
    {content}
</div>
</body>
</html>
""".format(style=style, content=content, errcode=errcode_html, ret_sample_data=ret_sample_data, menu=menu)
        return html

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
        html = self.get_doc_html(api_list)
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.finish(html)
