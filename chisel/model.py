#
# Copyright (C) 2012-2013 Craig Hobbs
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from .compat import basestring_, long_
from .struct import Struct

from datetime import datetime, timedelta, tzinfo
from decimal import Decimal
import time
import re
from uuid import UUID


# Floating point number with precision for JSON encoding
class JsonFloat(float):

    def __new__(cls, value, prec):
        return float.__new__(cls, value)

    def __init__(self, value, prec):
        self._formatString = '.' + str(prec) + 'f'

    def __repr__(self):
        return format(self, self._formatString).rstrip('0').rstrip('.')

    def __str__(self):
        return self.__repr__()


# Validation mode
VALIDATE_DEFAULT = 0
VALIDATE_QUERY_STRING = 1
VALIDATE_JSON_INPUT = 2
VALIDATE_JSON_OUTPUT = 3


# Type validation exception
class ValidationError(Exception):

    def __init__(self, msg, member = None):
        Exception.__init__(self, msg)
        self.member = member

    @classmethod
    def memberSyntax(cls, members):
        if members:
            return ''.join((('.' + x) if isinstance(x, basestring_) else ('[' + repr(x) + ']')) for x in members).lstrip('.')
        return None

    @classmethod
    def memberError(cls, typeInst, value, members, constraintSyntax = None):
        memberSyntax = cls.memberSyntax(members)
        msg = 'Invalid value ' + repr(value) + " (type '" + value.__class__.__name__ + "')" + \
              ((" for member '" + memberSyntax + "'") if memberSyntax else '') + \
              ", expected type '" + typeInst.typeName + "'" + \
              ((' [' + constraintSyntax + ']') if constraintSyntax else '')
        return ValidationError(msg, member = memberSyntax)


# Struct type
class TypeStruct(object):

    class Member(object):
        def __init__(self, name, typeInst, isOptional = False, doc = None):
            self.name = name
            self.typeInst = typeInst
            self.isOptional = isOptional
            self.doc = [] if doc is None else doc

    def __init__(self, typeName = 'struct', doc = None):

        self.typeName = typeName
        self.members = []
        self.doc = [] if doc is None else doc

    def addMember(self, name, typeInst, isOptional = False, doc = None):
        member = self.Member(name, typeInst, isOptional, doc)
        self.members.append(member)
        return member

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, dict):
            valueX = value
        elif isinstance(value, Struct):
            valueX = value()
            if not isinstance(valueX, dict):
                raise ValidationError.memberError(self, value, _member)
        elif mode == VALIDATE_QUERY_STRING and value == '':
            valueX = {}
        else:
            raise ValidationError.memberError(self, value, _member)

        # Result a copy?
        valueCopy = None if mode == VALIDATE_DEFAULT else {}

        # Validate members
        memberNames = set()
        for member in self.members:
            memberNames.add(member.name)

            # Is the required member not present?
            if member.name not in valueX:
                if not member.isOptional:
                    raise ValidationError("Required member '" + ValidationError.memberSyntax(_member + (member.name,)) + "' missing")
            else:
                # Validate the member value
                memberValue = member.typeInst.validate(valueX[member.name], mode, _member + (member.name,))
                if valueCopy is not None:
                    valueCopy[member.name] = memberValue

        # Check for invalid members
        for valueKey in valueX:
            if valueKey not in memberNames:
                raise ValidationError("Unknown member '" + ValidationError.memberSyntax(_member + (valueKey,)) + "'")

        return value if valueCopy is None else valueCopy


# Array type
class TypeArray(object):

    def __init__(self, typeInst, typeName = 'array'):

        self.typeName = typeName
        self.typeInst = typeInst

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, (list, tuple)):
            valueX = value
        elif isinstance(value, Struct):
            valueX = value()
            if not isinstance(valueX, (list, tuple)):
                raise ValidationError.memberError(self, value, _member)
        elif mode == VALIDATE_QUERY_STRING and value == '':
            valueX = []
        else:
            raise ValidationError.memberError(self, value, _member)

        # Result a copy?
        valueCopy = None if mode == VALIDATE_DEFAULT else []

        # Validate the list contents
        for ixArrayValue, arrayValue in enumerate(valueX):
            arrayValue = self.typeInst.validate(arrayValue, mode, _member + (ixArrayValue,))
            if valueCopy is not None:
                valueCopy.append(arrayValue)

        return value if valueCopy is None else valueCopy


# Dict type
class TypeDict(object):

    def __init__(self, typeInst, typeName = 'dict'):

        self.typeName = typeName
        self.typeInst = typeInst

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, dict):
            valueX = value
        elif isinstance(value, Struct):
            valueX = value()
            if not isinstance(valueX, dict):
                raise ValidationError.memberError(self, value, _member)
        elif mode == VALIDATE_QUERY_STRING and value == '':
            valueX = {}
        else:
            raise ValidationError.memberError(self, value, _member)

        # Result a copy?
        valueCopy = None if mode == VALIDATE_DEFAULT else {}

        # Validate the dict key/value pairs
        for key in valueX:

            # Dict keys must be strings
            if not isinstance(key, basestring_):
                raise ValidationError.memberError(TypeString(), key, _member + (key,))

            # Validate the value
            dictValue = self.typeInst.validate(valueX[key], mode, _member + (key,))
            if valueCopy is not None:
                valueCopy[key] = dictValue

        return value if valueCopy is None else valueCopy


# Enumeration type
class TypeEnum(object):

    class Value(object):
        def __init__(self, valueString, doc = None):
            self.value = valueString
            self.doc = [] if doc is None else doc

        def __eq__(self, other):
            return self.value == other

    def __init__(self, typeName = 'enum', doc = None):

        self.typeName = typeName
        self.values = []
        self.doc = [] if doc is None else doc

    def addValue(self, valueString, doc = None):
        value = self.Value(valueString, doc)
        self.values.append(value)
        return value

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate the value
        if value not in self.values:
            raise ValidationError.memberError(self, value, _member)

        return value


# String type
class TypeString(object):

    def __init__(self, typeName = 'string'):

        self.typeName = typeName
        self.constraint_len_lt = None
        self.constraint_len_lte = None
        self.constraint_len_gt = None
        self.constraint_len_gte = None

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate the value
        if not isinstance(value, basestring_):
            raise ValidationError.memberError(self, value, _member)

        # Check string constraints - lengths computed in unicode
        if self.constraint_len_lt is not None and not len(value) < self.constraint_len_lt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = 'len < ' + repr(self.constraint_len_lt))
        if self.constraint_len_lte is not None and not len(value) <= self.constraint_len_lte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = 'len <= ' + repr(self.constraint_len_lte))
        if self.constraint_len_gt is not None and not len(value) > self.constraint_len_gt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = 'len > ' + repr(self.constraint_len_gt))
        if self.constraint_len_gte is not None and not len(value) >= self.constraint_len_gte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = 'len >= ' + repr(self.constraint_len_gte))

        return value


# Int type
class TypeInt(object):

    def __init__(self, typeName = 'int'):

        self.typeName = typeName
        self.constraint_lt = None
        self.constraint_lte = None
        self.constraint_gt = None
        self.constraint_gte = None

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, (int, long_)) and not isinstance(value, bool):
            valueX = value
        elif isinstance(value, (float, Decimal)):
            valueX = int(value)
            if valueX != value:
                raise ValidationError.memberError(self, value, _member)
        elif mode == VALIDATE_QUERY_STRING and isinstance(value, basestring_):
            try:
                valueX = int(value)
            except:
                raise ValidationError.memberError(self, value, _member)
        else:
            raise ValidationError.memberError(self, value, _member)

        # Check constraints
        if self.constraint_lt is not None and not valueX < self.constraint_lt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '< ' + repr(self.constraint_lt))
        if self.constraint_lte is not None and not valueX <= self.constraint_lte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '<= ' + repr(self.constraint_lte))
        if self.constraint_gt is not None and not valueX > self.constraint_gt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '> ' + repr(self.constraint_gt))
        if self.constraint_gte is not None and not valueX >= self.constraint_gte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '>= ' + repr(self.constraint_gte))

        return value if mode == VALIDATE_DEFAULT else valueX


# Float type
class TypeFloat(object):

    def __init__(self, typeName = 'float'):

        self.typeName = typeName
        self.constraint_lt = None
        self.constraint_lte = None
        self.constraint_gt = None
        self.constraint_gte = None

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, float):
            valueX = value
        elif isinstance(value, (int, long_, Decimal)) and not isinstance(value, bool):
            valueX = float(value)
        elif mode == VALIDATE_QUERY_STRING and isinstance(value, basestring_):
            try:
                valueX = float(value)
            except:
                raise ValidationError.memberError(self, value, _member)
        else:
            raise ValidationError.memberError(self, value, _member)

        # Check constraints
        if self.constraint_lt is not None and not valueX < self.constraint_lt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '< ' + repr(self.constraint_lt))
        if self.constraint_lte is not None and not valueX <= self.constraint_lte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '<= ' + repr(self.constraint_lte))
        if self.constraint_gt is not None and not valueX > self.constraint_gt:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '> ' + repr(self.constraint_gt))
        if self.constraint_gte is not None and not valueX >= self.constraint_gte:
            raise ValidationError.memberError(self, value, _member, constraintSyntax = '>= ' + repr(self.constraint_gte))

        return value if mode == VALIDATE_DEFAULT else valueX


# Bool type
class TypeBool(object):

    VALUES = {
        'true' : True,
        'false': False
    }

    def __init__(self, typeName = 'bool'):

        self.typeName = typeName

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, bool):
            return value
        elif mode == VALIDATE_QUERY_STRING and isinstance(value, basestring_):
            try:
                return self.VALUES[value]
            except:
                raise ValidationError.memberError(self, value, _member)
        else:
            raise ValidationError.memberError(self, value, _member)


# Uuid type
class TypeUuid(object):

    def __init__(self, typeName = 'uuid'):

        self.typeName = typeName

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, UUID):
            valueX = value
        elif mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT) and isinstance(value, basestring_):
            try:
                valueX = UUID(value)
            except:
                raise ValidationError.memberError(self, value, _member)
        else:
            raise ValidationError.memberError(self, value, _member)

        # Convert to string for JSON output
        if mode == VALIDATE_JSON_OUTPUT:
            return str(valueX)

        return value if mode == VALIDATE_DEFAULT else valueX


# Datetime type
class TypeDatetime(object):

    def __init__(self, typeName = 'datetime'):

        self.typeName = typeName

    def validate(self, value, mode = VALIDATE_DEFAULT, _member = ()):

        # Validate and translate the value
        if isinstance(value, datetime):
            valueX = value
        elif mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT) and isinstance(value, basestring_):
            try:
                valueX = self.parseISO8601Datetime(value)
            except:
                raise ValidationError.memberError(self, value, _member)
        else:
            raise ValidationError.memberError(self, value, _member)

        # Set a time zone
        if mode != VALIDATE_DEFAULT and valueX.tzinfo is None:
            valueX = datetime(valueX.year, valueX.month, valueX.day, valueX.hour,
                              valueX.minute, valueX.second, valueX.microsecond, TypeDatetime.TZLocal())

        # Convert to string for JSON output
        if mode == VALIDATE_JSON_OUTPUT:
            return valueX.isoformat()

        return value if mode == VALIDATE_DEFAULT else valueX

    # GMT tzinfo class for parseISO8601Datetime (from Python docs)
    class TZUTC(tzinfo): # pragma: no cover

        def utcoffset(self, dt):
            return timedelta(0)

        def dst(self, dt):
            return timedelta(0)

        def tzname(self, dt):
            return 'UTC'

    # Local time zone tzinfo class (from Python docs)
    class TZLocal(tzinfo): # pragma: no cover

        def utcoffset(self, dt):
            if self._isdst(dt):
                return self._dstOffset()
            else:
                return self._stdOffset()

        def dst(self, dt):
            if self._isdst(dt):
                return self._dstOffset() - self._stdOffset()
            else:
                return timedelta(0)

        def tzname(self, dt):
            return time.tzname[self._isdst(dt)]

        @classmethod
        def _stdOffset(cls):
            return timedelta(seconds = -time.timezone)

        @classmethod
        def _dstOffset(cls):
            if time.daylight:
                return timedelta(seconds = -time.altzone)
            else:
                return cls._stdOffset()

        @classmethod
        def _isdst(cls, dt):
            tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, 0)
            stamp = time.mktime(tt)
            tt = time.localtime(stamp)
            return tt.tm_isdst > 0

    # ISO 8601 regex
    reISO8601 = re.compile('^\s*(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})' +
                           '(T(?P<hour>\d{2}):(?P<min>\d{2}?):(?P<sec>\d{2})([.,](?P<fracsec>\d{1,7}))?' +
                           '(Z|(?P<offsign>[+-])(?P<offhour>\d{2})(:?(?P<offmin>\d{2}))?))?\s*$')

    # Static helper function to parse ISO 8601 date/time
    @classmethod
    def parseISO8601Datetime(cls, s):

        # Match ISO 8601?
        m = cls.reISO8601.search(s)
        if not m:
            raise ValueError('Expected ISO 8601 date/time')

        # Extract ISO 8601 components
        year = int(m.group('year'))
        month = int(m.group('month'))
        day = int(m.group('day'))
        hour = int(m.group('hour')) if m.group('hour') else 0
        minute = int(m.group('min')) if m.group('min') else 0
        sec = int(m.group('sec')) if m.group('sec') else 0
        microsec = int(float('.' + m.group('fracsec')) * 1000000) if m.group('fracsec') else 0
        offhour = int(m.group('offsign') + m.group('offhour')) if m.group('offhour') else 0
        offmin = int(m.group('offsign') + m.group('offmin')) if m.group('offmin') else 0

        return (datetime(year, month, day, hour, minute, sec, microsec, cls.TZUTC()) -
                timedelta(hours = offhour, minutes = offmin))
