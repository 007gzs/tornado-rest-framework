#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import os
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache
from tornado.template import Loader
from jinja2 import defaults
from jinja2.runtime import Undefined
from tornadoapi.conf import settings
from tornadoapi.core import json_dumps

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


_JINJA_ENV.filters['to_json'] = json_dumps
for key in ('filters', 'test', 'globals'):
    cfg_data = cfg.get(key, {})
    if cfg_data:
        env_field = getattr(_JINJA_ENV, key)
        for name, ftr in cfg_data.items():
            env_field[name] = ftr


class Jinja2TemplateLoader(Loader):
    def __init__(self, root_directory='', **kwargs):
        super(Jinja2TemplateLoader, self).__init__(root_directory, **kwargs)
        path = os.path.abspath(root_directory)
        self._env = copy.deepcopy(_JINJA_ENV)
        self._env.loader.searchpath = [path]

        cache_dir = os.path.abspath(settings.TEMPLATE_CONFIG.get('cache_directory'))
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        _CACHE.directory = cache_dir

    def load(self, name, parent_path=None):
        with self.lock:
            if os.path.isabs(name):
                path, file = os.path.split(name)
                self._env.loader.searchpath = [path]
                template = self._env.get_template(file)
            else:
                template = self._env.get_template(name)
            template.generate = template.render
            return template

    def reset(self):
        if hasattr(self._env, 'bytecode_cache') and self._env.bytecode_cache:
            self._env.bytecode_cache.clear()
