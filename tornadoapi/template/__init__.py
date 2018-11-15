# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import os

import tornadoapi

from tornadoapi.template.jinja2_loader import Jinja2TemplateLoader

RESOURCE_PATH = os.path.join(os.path.dirname(tornadoapi.__file__), 'resource')
RESOURCE_LOADER = Jinja2TemplateLoader(RESOURCE_PATH)


def get_resource_template_html(template_name, loader=None, namespace=None, **kwargs):
    if loader is None:
        loader = RESOURCE_LOADER
    if namespace is None:
        namespace = dict()
    t = loader.load(template_name)
    namespace.update(kwargs)
    return t.generate(**namespace)
