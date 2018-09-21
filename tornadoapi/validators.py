# encoding: utf-8
from __future__ import absolute_import, unicode_literals

from tornadoapi.core.exceptions import ValidationError


def _validator_fail(code, message, params):
    message_string = message.format(**params)
    raise ValidationError(message_string, code)


class BaseValidator(object):
    message = 'Ensure this value is {limit_value} (it is {show_value}s).'
    code = 'limit_value'

    def __init__(self, limit_value, message=None, **kwargs):
        self.limit_value = limit_value
        self.params = kwargs
        if message:
            self.message = message

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned, 'value': value}
        if self.compare(cleaned, self.limit_value):
            params.update(self.params)
            _validator_fail(self.code, self.message, params)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.limit_value == other.limit_value and
            self.message == other.message and
            self.code == other.code
        )

    def compare(self, a, b):
        return a is not b

    def clean(self, x):
        return x


class MaxValueValidator(BaseValidator):
    message = 'Ensure this value is less than or equal to {limit_value}.'
    code = 'max_value'

    def compare(self, a, b):
        return a > b


class MinValueValidator(BaseValidator):
    message = 'Ensure this value is greater than or equal to {limit_value}.'
    code = 'min_value'

    def compare(self, a, b):
        return a < b


class MinLengthValidator(BaseValidator):
    message = 'Ensure this value has at least {limit_value} character (it has {show_value}).'
    code = 'min_length'

    def compare(self, a, b):
        return a < b

    def clean(self, x):
        return len(x)


class MaxLengthValidator(BaseValidator):
    message = 'Ensure this value has at most {limit_value} character (it has {show_value}).'
    code = 'max_length'

    def compare(self, a, b):
        return a > b

    def clean(self, x):
        return len(x)


class DecimalValidator(object):
    """
    Validate that the input does not exceed the maximum number of digits
    expected, otherwise raise ValidationError.
    """
    messages = {
        'max_digits': 'Ensure that there are no more than {max} digit in total.',
        'max_decimal_places': 'Ensure that there are no more than {max} decimal place.',
        'max_whole_digits': 'Ensure that there are no more than {max} digit before the decimal point.',
    }

    def __init__(self, max_digits, decimal_places):
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def __call__(self, value):
        digit_tuple, exponent = value.as_tuple()[1:]
        decimals = abs(exponent)
        # digit_tuple doesn't include any leading zeros.
        digits = len(digit_tuple)
        if decimals > digits:
            # We have leading zeros up to or past the decimal point. Count
            # everything past the decimal point as a digit. We do not count
            # 0 before the decimal point as a digit since that would mean
            # we would not allow max_digits = decimal_places.
            digits = decimals
        whole_digits = digits - decimals

        if self.max_digits is not None and digits > self.max_digits:
            _validator_fail('max_digits', self.messages['max_digits'], {'max': self.max_digits})
        if self.decimal_places is not None and decimals > self.decimal_places:
            _validator_fail('max_decimal_places', self.messages['max_decimal_places'], {'max': self.decimal_places})
        if (self.max_digits is not None and self.decimal_places is not None and
                whole_digits > (self.max_digits - self.decimal_places)):
            _validator_fail(
                'max_whole_digits',
                self.messages['max_whole_digits'],
                {'max': (self.max_digits - self.decimal_places)}
            )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.max_digits == other.max_digits and
            self.decimal_places == other.decimal_places
        )
