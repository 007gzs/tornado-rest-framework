# encoding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import decimal
import json
import re
from collections import OrderedDict

import six

from tornadoapi.conf import settings as api_settings
from tornadoapi.core import to_text
from tornadoapi.core.exceptions import ValidationError
from tornadoapi.validators import MaxLengthValidator, MinLengthValidator, MaxValueValidator, MinValueValidator


def to_choices_dict(choices):
    """
    Convert choices into key/value dicts.

    to_choices_dict([1]) -> {1: 1}
    to_choices_dict([(1, '1st'), (2, '2nd')]) -> {1: '1st', 2: '2nd'}
    to_choices_dict([('Group', ((1, '1st'), 2))]) -> {'Group': {1: '1st', 2: '2'}}
    """
    # Allow single, paired or grouped choices style:
    # choices = [1, 2, 3]
    # choices = [(1, 'First'), (2, 'Second'), (3, 'Third')]
    # choices = [('Category', ((1, 'First'), (2, 'Second'))), (3, 'Third')]
    ret = OrderedDict()
    for choice in choices:
        if not isinstance(choice, (list, tuple)):
            # single choice
            ret[choice] = choice
        else:
            key, value = choice
            if isinstance(value, (list, tuple)):
                # grouped choices (category, sub choices)
                ret[key] = to_choices_dict(value)
            else:
                # paired choice (key, display value)
                ret[key] = value
    return ret


def flatten_choices_dict(choices):
    """
    Convert a group choices dict into a flat dict of choices.

    flatten_choices_dict({1: '1st', 2: '2nd'}) -> {1: '1st', 2: '2nd'}
    flatten_choices_dict({'Group': {1: '1st', 2: '2nd'}}) -> {1: '1st', 2: '2nd'}
    """
    ret = OrderedDict()
    for key, value in choices.items():
        if isinstance(value, dict):
            # grouped choices (category, sub choices)
            for sub_key, sub_value in value.items():
                ret[sub_key] = sub_value
        else:
            # choice (key, display value)
            ret[key] = value
    return ret


class _Empty(object):

    def __nonzero__(self):
        return False

    def __str__(self):
        return '<empty>'


empty = _Empty()
NOT_REQUIRED_DEFAULT = 'May not set both `required` and `default`'
MISSING_ERROR_MESSAGE = (
    'ValidationError raised by `{class_name}`, but error key `{key}` does '
    'not exist in the `error_messages` dictionary.'
)


class Field(object):
    """
    参数基类

    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'required': '该参数必填',  # 'This field is required.',
        'null': '该参数不能为null',  # 'This field may not be null.'
    }
    default_validators = []
    initial = None

    def __init__(self, description=None, required=None, default=empty, help_text=None, raw_body=False,
                 error_messages=None, validators=None, allow_null=None, *args, **kwargs):
        if required is None:
            required = default is empty
        assert not (required and default is not empty), NOT_REQUIRED_DEFAULT
        self.description = description
        self.required = required
        self.default = default
        self.help_text = help_text
        self.raw_body = raw_body
        self.allow_null = allow_null
        if validators is not None:
            self.validators = validators[:]
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def get_field_info(self):
        return {
            'description': self.description,
            'type': self.__class__.__name__,
            'default': self.default,
            'help_text': self.help_text or '',
            'required': self.required,
            'ex_info': '; '.join(self._get_ex_info()),
            'raw_body': self.raw_body
        }

    def _get_ex_info(self):
        if hasattr(self, 'choices'):
            return ['{}: {}'.format(k, v) for k, v in self.choices.items()]
        help_text_li = []
        for att in ['max_value', 'min_value', 'max_length', 'min_length', 'max_digits', 'sep']:
            val = getattr(self, att, None)
            if val is not None:
                help_text_li.append('%s: %s' % (att, val))
        if hasattr(self, 'fields'):
            h_text = []
            for f in self.fields:
                if isinstance(f, Field):
                    h_text.append("%s" % f.__class__.__name__)
                elif type(f) == type:
                    h_text.append("%s" % f.__name__)
                else:
                    h_text.append('%s' % f)
            help_text_li.append("fields : (%s)" % ",".join(h_text))
        if hasattr(self, 'field'):
            if isinstance(self.field, Field):
                help_text_li.append("field : %s" % self.field.__class__.__name__)
            elif type(self.field) == type:
                help_text_li.append('field : %s' % self.field.__name__)
            else:
                help_text_li.append('field : %s' % self.field)
        return help_text_li

    @property
    def validators(self):
        if not hasattr(self, '_validators'):
            setattr(self, '_validators', self.get_validators())
        return getattr(self, '_validators')

    @validators.setter
    def validators(self, validators):
        setattr(self, '_validators', validators)

    def get_validators(self):
        return self.default_validators[:]

    def fail(self, key, **kwargs):
        try:
            msg = self.error_messages[key]
        except KeyError:
            class_name = self.__class__.__name__
            msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
            raise AssertionError(msg)
        message_string = msg.format(**kwargs)
        raise ValidationError(message_string, code=key)

    def get_default(self):
        if callable(self.default):
            if hasattr(self.default, 'set_context'):
                self.default.set_context(self)
            return self.default()
        return self.default

    def validate_empty_values(self, data):
        if data is empty:
            if self.required:
                self.fail('required')
            data = self.get_default()
            if data is empty:
                data = self.initial
            return True, data

        if data is None:
            if not self.allow_null:
                self.fail('null')
            return True, None

        return False, data

    def run_validation(self, data=empty):
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = self.to_python(data)
        self.run_validators(value)
        return value

    def run_validators(self, value):
        errors = []
        for validator in self.validators:
            if hasattr(validator, 'set_context'):
                validator.set_context(self)

            try:
                validator(value)
            except ValidationError as exc:
                if isinstance(exc.detail, dict):
                    raise
                errors.extend(exc.detail)
        if errors:
            raise ValidationError(errors)

    def to_python(self, data):
        raise NotImplementedError(
            '{cls}.to_python() must be implemented.'.format(
                cls=self.__class__.__name__
            )
        )


class BooleanField(Field):
    """
    布尔基类

    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '"{input}" 不是有效的布尔值'  # '"{input}" is not a valid boolean.'
    }
    default_empty_html = False
    initial = False
    TRUE_VALUES = {
        't', 'T',
        'y', 'Y', 'yes', 'YES',
        'true', 'True', 'TRUE',
        'on', 'On', 'ON',
        '1', 1,
        True
    }
    FALSE_VALUES = {
        'f', 'F',
        'n', 'N', 'no', 'NO',
        'false', 'False', 'FALSE',
        'off', 'Off', 'OFF',
        '0', 0, 0.0,
        False
    }
    NULL_VALUES = {'n', 'N', 'null', 'Null', 'NULL', '', None}

    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES and self.allow_null:
                return None
        except TypeError:  # Input is an unhashable type
            pass
        self.fail('invalid', input=data)


class CharField(Field):
    """
    字符串参数

    :param allow_blank: 是否允许为空串
    :param trim_whitespace: 是否清空首尾空格
    :param max_length: 最大长度
    :param min_length: 最小长度
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '不是有效的字符串',  # 'Not a valid string.',
        'blank': '该参数不能为空',  # 'This field may not be blank.',
        'max_length': '该参数长度超过最大限制 {max_length}',  # 'Ensure this field has no more than {max_length} characters.',
        'min_length': '该参数长度不足最小限制 {min_length}',  # 'Ensure this field has at least {min_length} characters.'
    }

    def __init__(self, *args, **kwargs):
        self.allow_blank = kwargs.pop('allow_blank', False)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        super(CharField, self).__init__(*args, **kwargs)
        if self.max_length is not None:
            self.validators.append(
                MaxLengthValidator(
                    self.max_length, message=self.error_messages['max_length'], max_length=self.max_length
                )
            )
        if self.min_length is not None:
            self.validators.append(
                MinLengthValidator(
                    self.max_length, message=self.error_messages['min_length'], max_length=self.min_length
                )
            )

    def run_validation(self, data=empty):
        # Test for the empty string here so that it does not get validated,
        # and so that subclasses do not need to handle it explicitly
        # inside the `to_internal_value()` method.
        if data == '' or (self.trim_whitespace and six.text_type(data).strip() == ''):
            if not self.allow_blank:
                self.fail('blank')
            return ''
        return super(CharField, self).run_validation(data)

    def to_python(self, data):
        if isinstance(data, bool) or not isinstance(data, six.string_types + six.integer_types + (float,)):
            self.fail('invalid')
        value = to_text(data)
        return value.strip() if self.trim_whitespace else value


class SplitCharField(CharField):
    """
    分割字符串参数

    :param sep: 分割标识
    :param field: 被分割后数据类型
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_field = CharField(allow_blank=True)

    def __init__(self, *args, **kwargs):
        self.sep = kwargs.pop('sep', ',')
        self.field = kwargs.pop('field', self.default_field)
        assert isinstance(self.field, Field)
        super(SplitCharField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(SplitCharField, self).to_python(value)
        if value:
            return list(map(self.field.to_python, value.split(self.sep)))
        else:
            return []

    def __iter__(self):
        raise RuntimeError()


class NumberField(Field):
    """
    数字类型参数

    :param max_value: 最大值
    :param min_value: 最小值
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '该参数不是有效数字',  # 'A valid integer is required.',
        'max_value': '该参数超过最大限制 {max_value}',  # 'Ensure this value is less than or equal to {max_value}.',
        'min_value': '该参数不足最小限制 {min_value}',  # 'Ensure this value is greater than or equal to {min_value}.',
        'max_string_length': '该参数长度过长',  # 'String value too large.'
    }
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, *args, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super(NumberField, self).__init__(*args, **kwargs)
        if self.max_value is not None:
            self.validators.append(
                MaxValueValidator(
                    self.max_value, message=self.error_messages['max_value'], max_value=self.max_value
                )
            )
        if self.min_value is not None:
            self.validators.append(
                MinValueValidator(
                    self.min_value, message=self.error_messages['min_value'], min_value=self.min_value
                )
            )

    def to_python(self, data):
        raise NotImplementedError


class IntegerField(NumberField):
    """
    整型类型参数

    :param max_value: 最大值
    :param min_value: 最小值
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    re_decimal = re.compile(r'\.0*\s*$')  # allow e.g. '1.0' as an int, but not '1.2'

    def __init__(self, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        if isinstance(data, six.text_type) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            data = int(self.re_decimal.sub('', str(data)))
        except (ValueError, TypeError):
            self.fail('invalid')
        return data


class FloatField(NumberField):
    """
    浮点类型参数

    :param max_value: 最大值
    :param min_value: 最小值
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    def __init__(self, *args, **kwargs):
        super(FloatField, self).__init__(*args, **kwargs)

    def to_python(self, data):

        if isinstance(data, six.text_type) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            return float(data)
        except (TypeError, ValueError):
            self.fail('invalid')


class DecimalField(NumberField):
    """
    Decimal类型参数

    :param max_digits: 整数位处长度限制
    :param decimal_places: 小数位数长度限制
    :param rounding: 截取方式
    :param max_value: 最大值
    :param min_value: 最小值
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '该参数不是有效数字',  # 'A valid number is required.',
        'max_value': '该参数超过最大限制 {max_value}',  # 'Ensure this value is less than or equal to {max_value}.',
        'min_value': '该参数不足最小限制 {min_value}',  # 'Ensure this value is greater than or equal to {min_value}.',
        'max_digits': '该参数整数位数超过 {max_digits}',  # 'Ensure that there are no more than {max_digits} digits in total.',
        'max_decimal_places': '该参数小数位数超过 {max_decimal_places}',
        # 'Ensure that there are no more than {max_decimal_places} decimal places.',
        'max_whole_digits': '该参数总位数超过 {max_whole_digits}',
        # 'Ensure that there are no more than {max_whole_digits} digits before the decimal point.',
        'max_string_length': '该参数长度过长',  # 'String value too large.'
    }

    def __init__(self, max_digits, decimal_places, rounding=None, *args, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places

        if self.max_digits is not None and self.decimal_places is not None:
            self.max_whole_digits = self.max_digits - self.decimal_places
        else:
            self.max_whole_digits = None

        super(DecimalField, self).__init__(*args, **kwargs)

        if rounding is not None:
            valid_roundings = [v for k, v in vars(decimal).items() if k.startswith('ROUND_')]
            assert rounding in valid_roundings, (
                'Invalid rounding option %s. Valid values for rounding are: %s' % (rounding, valid_roundings))
        self.rounding = rounding

    def to_python(self, data):
        """
        Validate that the input is a decimal number and return a Decimal
        instance.
        """

        data = to_text(data).strip()

        if len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            value = decimal.Decimal(data)
        except decimal.DecimalException:
            self.fail('invalid')

        # Check for NaN. It is the only value that isn't equal to itself,
        # so we can use this to identify NaN values.
        if value != value:
            self.fail('invalid')

        # Check for infinity and negative infinity.
        if value in (decimal.Decimal('Inf'), decimal.Decimal('-Inf')):
            self.fail('invalid')

        return self.quantize(self.validate_precision(value))

    def validate_precision(self, value):
        """
        Ensure that there are no more than max_digits in the number, and no
        more than decimal_places digits after the decimal point.

        Override this method to disable the precision validation for input
        values or to enhance it in any way you need to.
        """
        sign, digittuple, exponent = value.as_tuple()

        if exponent >= 0:
            # 1234500.0
            total_digits = len(digittuple) + exponent
            whole_digits = total_digits
            decimal_places = 0
        elif len(digittuple) > abs(exponent):
            # 123.45
            total_digits = len(digittuple)
            whole_digits = total_digits - abs(exponent)
            decimal_places = abs(exponent)
        else:
            # 0.001234
            total_digits = abs(exponent)
            whole_digits = 0
            decimal_places = total_digits

        if self.max_digits is not None and total_digits > self.max_digits:
            self.fail('max_digits', max_digits=self.max_digits)
        if self.decimal_places is not None and decimal_places > self.decimal_places:
            self.fail('max_decimal_places', max_decimal_places=self.decimal_places)
        if self.max_whole_digits is not None and whole_digits > self.max_whole_digits:
            self.fail('max_whole_digits', max_whole_digits=self.max_whole_digits)

        return value

    def quantize(self, value):
        """
        Quantize the decimal value to the configured precision.
        """
        if self.decimal_places is None:
            return value

        context = decimal.getcontext().copy()
        if self.max_digits is not None:
            context.prec = self.max_digits
        return value.quantize(
            decimal.Decimal('.1') ** self.decimal_places,
            rounding=self.rounding,
            context=context
        )


class DateTimeField(Field):
    """
    时间日期类型参数

    :param input_formats: 时间日期格式 默认为 settings.DATETIME_INPUT_FORMATS
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '时间格式错误，请使用 {format}',  # 'Datetime has wrong format. Use one of these formats instead: {format}.',
        'date': 'Expected a datetime but got a date.',
        'make_aware': 'Invalid datetime for the timezone "{timezone}".',
        'overflow': 'Datetime value out of range.'
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, input_formats=None, *args, **kwargs):
        if input_formats is not None:
            self.input_formats = input_formats
        super(DateTimeField, self).__init__(*args, **kwargs)

    def _parse_datetime(self, value, input_formats):

        for input_format in input_formats:
            try:
                parsed = self.datetime_parser(value, input_format)
                return parsed
            except (ValueError, TypeError):
                pass

        self.fail('invalid', format=', '.join(input_formats))

    def to_python(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.DATETIME_INPUT_FORMATS)

        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            self.fail('date')

        if isinstance(value, datetime.datetime):
            return value
        return self._parse_datetime(value, input_formats)


class DateField(DateTimeField):
    """
    日期类型参数

    :param input_formats: 日期格式 默认为 settings.DATE_INPUT_FORMATS
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '日期格式错误，请使用 {format}',  # 'Date has wrong format. Use one of these formats instead: {format}.',
        'datetime': 'Expected a date but got a datetime.',
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, *args, **kwargs):
        super(DateField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.DATE_INPUT_FORMATS)

        if isinstance(value, datetime.datetime):
            self.fail('datetime')

        if isinstance(value, datetime.date):
            return value

        return self._parse_datetime(value, input_formats).date()


class TimeField(DateTimeField):
    """
    时间类型参数

    :param input_formats: 时间格式 默认为 settings.TIME_INPUT_FORMATS
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '时间格式错误，请使用 {format}',  # 'Time has wrong format. Use one of these formats instead: {format}.',
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, *args, **kwargs):
        super(TimeField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.TIME_INPUT_FORMATS)

        if isinstance(value, datetime.time):
            return value
        return self._parse_datetime(value, input_formats).date()


class ChoiceField(Field):
    """
    选择类型参数

    :param choices: 选项列表 支持格式： [1],  [(1, '1st'), (2, '2nd')], [('Group', ((1, '1st'), 2))]
    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid_choice': '"{input}" 不在可选列表中'  # '"{input}" is not a valid choice.'
    }

    def __init__(self, choices, *args, **kwargs):
        self.choices = choices

        self.allow_blank = kwargs.pop('allow_blank', False)

        super(ChoiceField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_strings_to_values[six.text_type(data)]
        except KeyError:
            self.fail('invalid_choice', input=data)

    def _get_choices(self):
        return self._choices

    def _set_choices(self, choices):
        self.grouped_choices = to_choices_dict(choices)
        self._choices = flatten_choices_dict(self.grouped_choices)

        # Map the string representation of choices to the underlying value.
        # Allows us to deal with eg. integer choices while supporting either
        # integer or string input, but still get the correct datatype out.
        self.choice_strings_to_values = {
            six.text_type(key): key for key in self.choices
        }

    choices = property(_get_choices, _set_choices)


class JSONField(Field):
    """
    选择类型参数

    :param description: 名称
    :param required: 是否必填
    :param default: 默认值
    :param help_text: 说明
    :param raw_body: 是否从POST BODY 原始数据获取
    :param error_messages: 错误信息
    :param validators: 检查器
    :param allow_null: 是否允许为None
    """
    default_error_messages = {
        'invalid': '该参数不是有效 JSON'  # 'Value must be valid JSON.'
    }

    def __init__(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        try:
            return json.loads(data)
        except (TypeError, ValueError):
            self.fail('invalid')
