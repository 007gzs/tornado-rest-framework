#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache
from tornado.template import Loader
from jinja2 import defaults
from jinja2.runtime import Undefined
from tornadoapi.conf import settings

_CACHE = FileSystemBytecodeCache()
_LOADER = FileSystemLoader([])
cfg = settings.TEMPLATE_CONFIG
_JINJA_ENV = Environment(bytecode_cache=_CACHE,
                         autoescape=cfg.get('autoescape', False),
                         cache_size=cfg.get('cache_size', 50),
                         auto_reload=cfg.get('filesystem_checks', True),
                         loader=_LOADER,
                         block_start_string=cfg.get('block_start_string', defaults.BLOCK_START_STRING),
                         block_end_string=cfg.get('block_end_string', defaults.BLOCK_END_STRING),
                         variable_start_string=cfg.get('variable_start_string', defaults.VARIABLE_START_STRING),
                         variable_end_string=cfg.get('variable_end_string', defaults.VARIABLE_END_STRING),
                         comment_start_string=cfg.get('comment_start_string', defaults.COMMENT_START_STRING),
                         comment_end_string=cfg.get('comment_end_string', defaults.COMMENT_END_STRING),
                         line_statement_prefix=cfg.get('line_statement_prefix', defaults.LINE_STATEMENT_PREFIX),
                         line_comment_prefix=cfg.get('line_comment_prefix', defaults.LINE_COMMENT_PREFIX),
                         trim_blocks=cfg.get('trim_blocks', defaults.TRIM_BLOCKS),
                         lstrip_blocks=cfg.get('lstrip_blocks', defaults.LSTRIP_BLOCKS),
                         newline_sequence=cfg.get('newline_sequence', defaults.NEWLINE_SEQUENCE),
                         keep_trailing_newline=cfg.get('keep_trailing_newline', defaults.KEEP_TRAILING_NEWLINE),
                         extensions=cfg.get('extensions', ()),
                         optimized=cfg.get('optimized', True),
                         undefined=cfg.get('undefined', Undefined),
                         finalize=cfg.get('finalize', None))

_JINJA_ENV.filters['to_json'] = json.dumps


class Jinja2TemplateLoader(Loader):
    def __init__(self, root_directory='', **kwargs):
        super(Jinja2TemplateLoader, self).__init__(root_directory, **kwargs)
        path = os.path.abspath(root_directory)
        _JINJA_ENV.loader.searchpath = [path]

        cache_dir = os.path.abspath(settings.TEMPLATE_CONFIG.get('cache_directory'))
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        _CACHE.directory = cache_dir

    def load(self, name, parent_path=None):
        with self.lock:
            if os.path.isabs(name):
                path, file = os.path.split(name)
                _JINJA_ENV.loader.searchpath = [path]
                template = _JINJA_ENV.get_template(file)
            else:
                template = _JINJA_ENV.get_template(name)
            template.generate = template.render
            return template

    def reset(self):
        if hasattr(_JINJA_ENV, 'bytecode_cache') and _JINJA_ENV.bytecode_cache:
            _JINJA_ENV.bytecode_cache.clear()
