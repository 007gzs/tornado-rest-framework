# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import re
import sys

import six

import tornadoapi
from tornadoapi.conf import settings
from tornadoapi.core import escape, to_text, pprint

HIDDEN_SETTINGS = re.compile('API|TOKEN|KEY|SECRET|PASS|SIGNATURE', flags=re.IGNORECASE)

CLEANSED_SUBSTITUTE = '********************'


class CallableSettingWrapper(object):
    """ Object to wrap callable appearing in settings

    * Not to call in the debug page (#21345).
    * Not to break the debug page if the callable forbidding to set attributes (#23070).
    """
    def __init__(self, callable_setting):
        self._wrapped = callable_setting

    def __repr__(self):
        return repr(self._wrapped)


def cleanse_setting(key, value):
    """Cleanse an individual setting key/value of sensitive content.

    If the value is a dictionary, recursively cleanse the keys in
    that dictionary.
    """
    try:
        if HIDDEN_SETTINGS.search(key):
            cleansed = CLEANSED_SUBSTITUTE
        else:
            if isinstance(value, dict):
                cleansed = {k: cleanse_setting(k, v) for k, v in value.items()}
            else:
                cleansed = value
    except TypeError:
        # If the key isn't regex-able, just return as-is.
        cleansed = value

    if callable(cleansed):
        # For fixing #21345 and #23070
        cleansed = CallableSettingWrapper(cleansed)

    return cleansed


def get_safe_settings():
    """
    Returns a dictionary of the settings module, with sensitive settings blurred out.
    """
    settings_dict = {}
    for k in dir(settings):
        if k.isupper():
            settings_dict[k] = cleanse_setting(k, getattr(settings, k))
    return settings_dict


def get_safe_app_settings(handler):
    """
    Returns a dictionary of the app_settings module, with sensitive app_settings blurred out.
    """
    settings_dict = {}
    if handler is not None:
        for k, v in handler.settings.items():
            settings_dict[k] = cleanse_setting(k, v)
    return settings_dict


class ExceptionReporterFilter(object):
    """
    Base for all exception reporter filter classes. All overridable hooks
    contain lenient default behaviors.
    """

    def get_post_parameters(self, handler):
        if handler is None:
            return {}
        else:
            return handler.request.body_arguments

    def get_traceback_frame_variables(self, handler, tb_frame):
        return list(tb_frame.f_locals.items())


class SafeExceptionReporterFilter(ExceptionReporterFilter):
    """
    Use annotations made by the sensitive_post_parameters and
    sensitive_variables decorators to filter out sensitive information.
    """

    def is_active(self, handler):
        """
        This filter is to add safety in production environments (i.e. DEBUG
        is False). If DEBUG is True then your site is not safe anyway.
        This hook is provided as a convenience to easily activate or
        deactivate the filter on a per request basis.
        """
        return settings.DEBUG is False

    def get_post_parameters(self, handler):
        """
        Replaces the values of POST parameters marked as sensitive with
        stars (*********).
        """
        if handler is None:
            return {}
        else:
            sensitive_post_parameters = getattr(handler, 'sensitive_post_parameters', [])
            if self.is_active(handler) and sensitive_post_parameters:
                cleansed = handler.request.body_arguments.copy()
                if sensitive_post_parameters == '__ALL__':
                    # Cleanse all parameters.
                    for k, v in cleansed.items():
                        cleansed[k] = CLEANSED_SUBSTITUTE
                    return cleansed
                else:
                    # Cleanse only the specified parameters.
                    for param in sensitive_post_parameters:
                        if param in cleansed:
                            cleansed[param] = CLEANSED_SUBSTITUTE
                    return cleansed
            else:
                return handler.request.body_arguments

    def get_traceback_frame_variables(self, handler, tb_frame):
        """
        Replaces the values of variables marked as sensitive with
        stars (*********).
        """
        # Loop through the frame's callers to see if the sensitive_variables
        # decorator was used.
        current_frame = tb_frame.f_back
        sensitive_variables = None
        while current_frame is not None:
            if (current_frame.f_code.co_name == 'sensitive_variables_wrapper' and
                    'sensitive_variables_wrapper' in current_frame.f_locals):
                # The sensitive_variables decorator was used, so we take note
                # of the sensitive variables' names.
                wrapper = current_frame.f_locals['sensitive_variables_wrapper']
                sensitive_variables = getattr(wrapper, 'sensitive_variables', None)
                break
            current_frame = current_frame.f_back

        cleansed = {}
        if self.is_active(handler) and sensitive_variables:
            if sensitive_variables == '__ALL__':
                # Cleanse all variables
                for name, value in tb_frame.f_locals.items():
                    cleansed[name] = CLEANSED_SUBSTITUTE
            else:
                # Cleanse specified variables
                for name, value in tb_frame.f_locals.items():
                    if name in sensitive_variables:
                        value = CLEANSED_SUBSTITUTE
                    cleansed[name] = value
        else:
            # Potentially cleanse the request and any MultiValueDicts if they
            # are one of the frame variables.
            for name, value in tb_frame.f_locals.items():
                cleansed[name] = value

        if (tb_frame.f_code.co_name == 'sensitive_variables_wrapper' and
                'sensitive_variables_wrapper' in tb_frame.f_locals):
            # For good measure, obfuscate the decorated function's arguments in
            # the sensitive_variables decorator's frame, in case the variables
            # associated with those arguments were meant to be obfuscated from
            # the decorated function's frame.
            cleansed['func_args'] = CLEANSED_SUBSTITUTE
            cleansed['func_kwargs'] = CLEANSED_SUBSTITUTE

        return cleansed.items()


class ExceptionReporter(object):
    """
    A class to organize and coordinate reporting on exceptions.
    """
    def __init__(self, handler, exc_type, exc_value, tb, is_email=False):
        self.handler = handler
        self.filter = SafeExceptionReporterFilter()
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        self.is_email = is_email

        self.template_info = getattr(self.exc_value, 'template_debug', None)
        self.template_does_not_exist = False
        self.postmortem = None

    def get_traceback_data(self):
        """Return a dictionary containing traceback information."""

        frames = self.get_traceback_frames()
        for i, frame in enumerate(frames):
            if 'vars' in frame:
                frame_vars = []
                for k, v in frame['vars']:
                    v = pprint(v)
                    # The force_escape filter assume unicode, make sure that works
                    if isinstance(v, six.binary_type):
                        v = v.decode('utf-8', 'replace')  # don't choke on non-utf-8 input
                    # Trim large blobs of data
                    if len(v) > 4096:
                        v = '%s... <trimmed %d bytes string>' % (v[0:4096], len(v))
                    frame_vars.append((k, escape(v)))
                frame['vars'] = frame_vars
            frames[i] = frame

        unicode_hint = ''
        if self.exc_type and issubclass(self.exc_type, UnicodeError):
            start = getattr(self.exc_value, 'start', None)
            end = getattr(self.exc_value, 'end', None)
            if start is not None and end is not None:
                unicode_str = self.exc_value.args[1]
                unicode_hint = to_text(unicode_str[max(start - 5, 0):min(end + 5, len(unicode_str))], 'ascii')
        from tornado import version
        if self.handler is None:
            user_str = None
        else:
            try:
                user_str = to_text(self.handler.current_user)
            except Exception:
                # request.user may raise OperationalError if the database is
                # unavailable, for example.
                user_str = '[unable to retrieve the current user]'

        c = {
            'is_email': self.is_email,
            'unicode_hint': unicode_hint,
            'frames': frames,
            'handler': self.handler,
            'user_str': user_str,
            'filtered_POST_items': list(self.filter.get_post_parameters(self.handler).items()),
            'settings': get_safe_settings(),
            'app_settings': get_safe_app_settings(self.handler),
            'sys_executable': sys.executable,
            'sys_version_info': '%d.%d.%d' % sys.version_info[0:3],
            'server_time': datetime.datetime.now(),
            'tornado_version_info': version,
            'tornadoapi_version_info': tornadoapi.__version__,
            'sys_path': sys.path,
            'template_info': self.template_info,
            'template_does_not_exist': self.template_does_not_exist,
            'postmortem': self.postmortem,
        }
        if self.handler is not None:
            c['request_GET_items'] = self.handler.request.query_arguments.items()
            c['request_FILES_items'] = self.handler.request.files.items()
            c['request_COOKIES_items'] = self.handler.request.cookies.items()
        # Check whether exception info is available
        if self.exc_type:
            c['exception_type'] = self.exc_type.__name__
        if self.exc_value:
            c['exception_value'] = to_text(self.exc_value)
        if frames:
            c['lastframe'] = frames[-1]
        return c

    def get_traceback_html(self):
        """
        Return HTML version of debug 500 HTTP error page.
        """
        from tornadoapi.template import get_resource_template_html
        return get_resource_template_html('technical_500.html', **self.get_traceback_data())

    def get_traceback_text(self):
        """
        Return plain text version of debug 500 HTTP error page.
        """
        from tornadoapi.template import get_resource_template_html
        return get_resource_template_html('technical_500.txt', **self.get_traceback_data())

    def _get_lines_from_file(self, filename, lineno, context_lines, loader=None, module_name=None):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        source = None
        if loader is not None and hasattr(loader, "get_source"):
            try:
                source = loader.get_source(module_name)
            except ImportError:
                pass
            if source is not None:
                source = source.splitlines()
        if source is None:
            try:
                with open(filename, 'rb') as fp:
                    source = fp.read().splitlines()
            except (OSError, IOError):
                pass
        if source is None:
            return None, [], None, []

        # If we just read the source from a file, or if the loader did not
        # apply tokenize.detect_encoding to decode the source into a Unicode
        # string, then we should do that ourselves.
        if isinstance(source[0], six.binary_type):
            encoding = 'ascii'
            for line in source[:2]:
                # File coding may be specified. Match pattern from PEP-263
                # (http://www.python.org/dev/peps/pep-0263/)
                match = re.search(br'coding[:=]\s*([-\w.]+)', line)
                if match:
                    encoding = match.group(1).decode('ascii')
                    break
            source = [six.text_type(sline, encoding, 'replace') for sline in source]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        pre_context = source[lower_bound:lineno]
        context_line = source[lineno]
        post_context = source[lineno + 1:upper_bound]

        return lower_bound, pre_context, context_line, post_context

    def get_traceback_frames(self):
        def explicit_or_implicit_cause(exc_value):
            explicit = getattr(exc_value, '__cause__', None)
            implicit = getattr(exc_value, '__context__', None)
            return explicit or implicit

        # Get the exception and all its causes
        exceptions = []
        exc_value = self.exc_value
        while exc_value:
            exceptions.append(exc_value)
            exc_value = explicit_or_implicit_cause(exc_value)

        frames = []
        # No exceptions were supplied to ExceptionReporter
        if not exceptions:
            return frames

        # In case there's just one exception (always in Python 2,
        # sometimes in Python 3), take the traceback from self.tb (Python 2
        # doesn't have a __traceback__ attribute on Exception)
        exc_value = exceptions.pop()
        tb = self.tb if six.PY2 or not exceptions else exc_value.__traceback__

        while tb is not None:
            # Support for __traceback_hide__ which is used by a few libraries
            # to hide internal frames.
            if tb.tb_frame.f_locals.get('__traceback_hide__'):
                tb = tb.tb_next
                continue
            filename = tb.tb_frame.f_code.co_filename
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno - 1
            loader = tb.tb_frame.f_globals.get('__loader__')
            module_name = tb.tb_frame.f_globals.get('__name__') or ''
            pre_context_lineno, pre_context, context_line, post_context = self._get_lines_from_file(
                filename, lineno, 7, loader, module_name,
            )
            if pre_context_lineno is not None:
                frames.append({
                    'exc_cause': explicit_or_implicit_cause(exc_value),
                    'exc_cause_explicit': getattr(exc_value, '__cause__', True),
                    'tb': tb,
                    'type': 'django' if module_name.startswith('django.') else 'user',
                    'filename': filename,
                    'function': function,
                    'lineno': lineno + 1,
                    'vars': self.filter.get_traceback_frame_variables(self.handler, tb.tb_frame),
                    'id': id(tb),
                    'pre_context': pre_context,
                    'context_line': context_line,
                    'post_context': post_context,
                    'pre_context_lineno': pre_context_lineno + 1,
                })

            # If the traceback for current exception is consumed, try the
            # other exception.
            if six.PY2:
                tb = tb.tb_next
            elif not tb.tb_next and exceptions:
                exc_value = exceptions.pop()
                tb = exc_value.__traceback__
            else:
                tb = tb.tb_next

        return frames

    def format_exception(self):
        """
        Return the same data as from traceback.format_exception.
        """
        import traceback
        frames = self.get_traceback_frames()
        tb = [(f['filename'], f['lineno'], f['function'], f['context_line']) for f in frames]
        lis = ['Traceback (most recent call last):\n']
        lis += traceback.format_list(tb)
        lis += traceback.format_exception_only(self.exc_type, self.exc_value)
        return lis
