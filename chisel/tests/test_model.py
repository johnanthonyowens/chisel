#
# Copyright (C) 2012-2016 Craig Hobbs
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

from datetime import date, datetime
from decimal import Decimal
import unittest
from uuid import UUID

from chisel.model import StructMemberAttributes, ValidationError, AttributeValidationError, \
    VALIDATE_DEFAULT, VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT, IMMUTABLE_VALIDATION_MODES, \
    Typedef, TypeStruct, TypeArray, TypeDict, TypeEnum, \
    TYPE_STRING, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_UUID, TYPE_DATE, TYPE_DATETIME, TYPE_OBJECT
from chisel.util import TZUTC, TZLOCAL


ALL_VALIDATION_MODES = (VALIDATE_DEFAULT, VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT)


class TestModelValidationError(unittest.TestCase):

    def test_member_syntax_dict_single(self):
        self.assertEqual(ValidationError.member_syntax(('a',)), 'a')

    def test_member_syntax_dict_nested(self):
        self.assertEqual(ValidationError.member_syntax(('a', 'b', 'c')), 'a.b.c')

    def test_member_syntax_array_single(self):
        self.assertEqual(ValidationError.member_syntax((0,)), '[0]')

    def test_member_syntax_array_nested(self):
        self.assertEqual(ValidationError.member_syntax((0, 1, 0)), '[0][1][0]')

    def test_member_syntax_mixed(self):
        self.assertEqual(ValidationError.member_syntax(('a', 1, 'b')), 'a[1].b')

    def test_member_syntax_mixed2(self):
        self.assertEqual(ValidationError.member_syntax((1, 'a', 0)), '[1].a[0]')

    def test_member_syntax_empty(self):
        self.assertEqual(ValidationError.member_syntax(()), None)

    def test_member_syntax_none(self):
        self.assertEqual(ValidationError.member_syntax(None), None)

    def test_member_error_basic(self):

        exc = ValidationError.member_error(TYPE_INT, 'abc', ('a',))
        self.assertTrue(isinstance(exc, Exception))
        self.assertTrue(isinstance(exc, ValidationError))
        self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member 'a', expected type 'int'")
        self.assertEqual(exc.member, 'a')

    def test_member_error_no_member(self):

        exc = ValidationError.member_error(TYPE_INT, 'abc', ())
        self.assertTrue(isinstance(exc, Exception))
        self.assertTrue(isinstance(exc, ValidationError))
        self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'int'")
        self.assertEqual(exc.member, None)

    def test_member_error_constraint(self):

        exc = ValidationError.member_error(TYPE_INT, 6, ('a',), constraint_syntax='< 5')
        self.assertTrue(isinstance(exc, Exception))
        self.assertTrue(isinstance(exc, ValidationError))
        self.assertEqual(str(exc), "Invalid value 6 (type 'int') for member 'a', expected type 'int' [< 5]")
        self.assertEqual(exc.member, 'a')


class TestStructMemberAttributes(unittest.TestCase):

    def test_validate_eq(self):
        attr = StructMemberAttributes(op_eq=5)
        attr.validate(5)
        try:
            attr.validate(4)
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 4 (type 'int') [== 5]")
        else:
            self.fail()

    def test_validate_lt(self):
        attr = StructMemberAttributes(op_lt=5)
        attr.validate(4)
        try:
            attr.validate(5)
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 5 (type 'int') [< 5]")
        else:
            self.fail()

    def test_validate_lte(self):
        attr = StructMemberAttributes(op_lte=5)
        attr.validate(5)
        try:
            attr.validate(6)
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 6 (type 'int') [<= 5]")
        else:
            self.fail()

    def test_validate_gt(self):
        attr = StructMemberAttributes(op_gt=5)
        attr.validate(6)
        try:
            attr.validate(5)
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 5 (type 'int') [> 5]")
        else:
            self.fail()

    def test_validate_gte(self):
        attr = StructMemberAttributes(op_gte=5)
        attr.validate(5)
        try:
            attr.validate(4)
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 4 (type 'int') [>= 5]")
        else:
            self.fail()

    def test_validate_len_eq(self):
        attr = StructMemberAttributes(op_len_eq=3)
        attr.validate('abc')
        try:
            attr.validate('ab')
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 'ab' (type 'str') [len == 3]")
        else:
            self.fail()

    def test_validate_len_lt(self):
        attr = StructMemberAttributes(op_len_lt=3)
        attr.validate('ab')
        try:
            attr.validate('abc')
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') [len < 3]")
        else:
            self.fail()

    def test_validate_len_lte(self):
        attr = StructMemberAttributes(op_len_lte=3)
        attr.validate('abc')
        try:
            attr.validate('abcd')
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 'abcd' (type 'str') [len <= 3]")
        else:
            self.fail()

    def test_validate_len_gt(self):
        attr = StructMemberAttributes(op_len_gt=3)
        attr.validate('abcd')
        try:
            attr.validate('abc')
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') [len > 3]")
        else:
            self.fail()

    def test_validate_len_gte(self):
        attr = StructMemberAttributes(op_len_gte=3)
        attr.validate('abc')
        try:
            attr.validate('ab')
        except ValidationError as exc:
            self.assertEqual(str(exc), "Invalid value 'ab' (type 'str') [len >= 3]")
        else:
            self.fail()


class TestModelTypedefValidation(unittest.TestCase):

    # Test typedef type construction
    def test_init(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gt=5))
        self.assertEqual(type_.type_name, 'typedef')
        self.assertTrue(isinstance(type_.type, type(TYPE_INT)))
        self.assertTrue(isinstance(type_.attr, StructMemberAttributes))
        self.assertEqual(type_.doc, [])

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gt=5), type_name='Foo', doc=['A', 'B'])
        self.assertEqual(type_.type_name, 'Foo')
        self.assertTrue(isinstance(type_.type, type(TYPE_INT)))
        self.assertTrue(isinstance(type_.attr, StructMemberAttributes))
        self.assertEqual(type_.doc, ['A', 'B'])

    # Test typedef attribute validation
    def test_validate_attr(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gt=5))

        type_.validate_attr(StructMemberAttributes())

        type_.validate_attr(StructMemberAttributes(op_gt=7))

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - success
    def test_validate(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gte=5))

        obj = 5
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - success
    def test_validate_no_attr(self):

        type_ = Typedef(TYPE_INT)

        obj = 5
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # Query string validation mode - transformed value
    def test_validate_transformed_value(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gte=5))

        obj = '5'
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, 5)

    # Query string validation mode - transformed value
    def test_validate_type_error(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gte=5))

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'int'")
            else:
                self.fail()

    # Query string validation mode - transformed value
    def test_validate_attr_error(self):

        type_ = Typedef(TYPE_INT, StructMemberAttributes(op_gte=5))

        obj = 4
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 4 (type 'int') [>= 5]")
            else:
                self.fail()


class TestModelStructValidation(unittest.TestCase):

    # Test struct type construction
    def test_init(self):

        type_ = TypeStruct()
        type_members = list(type_.members())
        self.assertEqual(type_.type_name, 'struct')
        self.assertEqual(type_.union, False)
        self.assertEqual(type_members, [])
        self.assertEqual(type_.doc, [])

        type_.add_member('a', TypeStruct())
        type_members = list(type_.members())
        self.assertEqual(len(type_members), 1)
        self.assertEqual(type_members[0].name, 'a')
        self.assertTrue(isinstance(type_members[0].type, TypeStruct))
        self.assertEqual(type_members[0].optional, False)
        self.assertEqual(type_members[0].nullable, False)
        self.assertEqual(type_members[0].doc, [])

    # Test union type construction
    def test_init_union(self):

        type_ = TypeStruct(union=True)
        type_members = list(type_.members())
        self.assertEqual(type_.type_name, 'union')
        self.assertEqual(type_.union, True)
        self.assertEqual(type_members, [])
        self.assertEqual(type_.doc, [])

        type_.add_member('a', TypeStruct())
        type_members = list(type_.members())
        self.assertEqual(len(type_members), 1)
        self.assertEqual(type_members[0].name, 'a')
        self.assertTrue(isinstance(type_members[0].type, TypeStruct))
        self.assertEqual(type_members[0].optional, True)
        self.assertEqual(type_members[0].nullable, False)
        self.assertEqual(type_members[0].doc, [])

    # Test struct with base types
    def test_base_types(self):

        base_type = TypeStruct()
        base_type.add_member('a', TYPE_INT)
        base_type.add_member('b', TYPE_FLOAT)

        base_type2 = TypeStruct()
        base_type2.add_member('c', TYPE_STRING)
        base_type2.add_member('d', TYPE_BOOL)

        type_ = TypeStruct(base_types=[base_type, base_type2])
        type_.add_member('e', TYPE_UUID)
        type_.add_member('f', TYPE_DATETIME)

        self.assertEqual([(m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in type_.members()], [
            ('a', 'int', False, False, []),
            ('b', 'float', False, False, []),
            ('c', 'string', False, False, []),
            ('d', 'bool', False, False, []),
            ('e', 'uuid', False, False, []),
            ('f', 'datetime', False, False, [])
        ])
        self.assertEqual([(m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in type_.members(include_base_types=False)], [
            ('e', 'uuid', False, False, []),
            ('f', 'datetime', False, False, [])
        ])

    # All validation modes - success
    def test_validation(self):

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING)

        obj = {'a': 7, 'b': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 'abc'})

    # All validation modes - union success
    def test_validation_union(self):

        type_ = TypeStruct(union=True)
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING)

        obj = {'a': 7}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7})

        obj = {'b': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'b': 'abc'})

    # All validation modes - struct with base types success
    def test_validation_base_types(self):

        base_type = TypeStruct()
        base_type.add_member('a', TYPE_INT)

        base_type2 = TypeStruct()
        base_type2.add_member('b', TYPE_STRING)

        type_ = TypeStruct(base_types=[base_type, base_type2])
        type_.add_member('c', TYPE_BOOL)

        obj = {'a': 7, 'b': 'abc', 'c': True}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 'abc', 'c': True})

    # All validation modes - optional member present
    def test_validation_optional_present(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, optional=True)

        obj = {'a': 7, 'b': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 'abc'})

    # All validation modes - optional member missing
    def test_validation_optional_missing(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, optional=True)

        obj = {'a': 7}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7})

    # All validation modes - nullable member present and non-null
    def test_validation_nullable_present_non_null(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, nullable=True)

        obj = {'a': 7, 'b': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 'abc'})

    # All validation modes - nullable member present and null
    def test_validation_nullable_present_null(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, nullable=True)

        obj = {'a': 7, 'b': None}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': None})

    # All validation modes - nullable member with attributes present
    def test_validation_nullable_attr(self):

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_INT, nullable=True, attr=StructMemberAttributes(op_lt=5))

        obj = {'a': 7, 'b': 4}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 4})

        obj = {'a': 7, 'b': 5}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 5 (type 'int') for member 'b' [< 5]")
            else:
                self.fail()

        obj = {'a': 7, 'b': None}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': None})

    # All validation modes - nullable member present and 'null' string for non-string member
    def test_validation_nullable_present_null_string(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_INT, nullable=True)

        obj = {'a': 7, 'b': 'null'}
        for mode in ALL_VALIDATION_MODES:
            if mode == VALIDATE_QUERY_STRING:
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
                self.assertEqual(obj2, {'a': 7, 'b': None})
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value 'null' (type 'str') for member 'b', expected type 'int'")
                else:
                    self.fail()

    # All validation modes - nullable member present and 'null' string for string member
    def test_validation_nullable_present_null_string_type(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, nullable=True)

        obj = {'a': 7, 'b': 'null'}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 'null'})

    # All validation modes - nullable member missing
    def test_validation_nullable_missing(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING, nullable=True)

        obj = {'a': 7}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Required member 'b' missing")
            else:
                self.fail()

    # All validation modes - member with attributes - valid
    def test_validation_member_attributes_valid(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = {'a': 4}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 4})

    # All validation modes - member with attributes - invalid
    def test_validation_member_attributes_invalid(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = {'a': 7}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7 (type 'int') for member 'a' [< 5]")
            else:
                self.fail()

    # All validation modes - nested structure
    def test_validation_nested(self):

        type_ = TypeStruct()
        type2 = TypeStruct()
        type_.add_member('a', type2)
        type2.add_member('b', TYPE_INT)

        obj = {'a': {'b': 7}}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
                self.assertTrue(obj['a'] is obj2['a'])
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(obj['a'] is not obj2['a'])
                self.assertTrue(isinstance(obj2, dict))
                self.assertTrue(isinstance(obj2['a'], dict))
            self.assertEqual(obj2, {'a': {'b': 7}})

    # Query string validation mode - transformed member
    def test_validation_query_string_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)

        obj = {'a': '7'}
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {'a': 7})

    # Query string validation mode - empty string
    def test_validation_query_string_empty_string(self): # pylint: disable=invalid-name

        type_ = TypeStruct()

        obj = ''
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {})

    # JSON input validation mode - transformed member
    def test_validation_json_input_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_UUID)

        obj = {'a': '184EAB31-4307-416C-AAC4-3B92B2358677'}
        obj2 = type_.validate(obj, mode=VALIDATE_JSON_INPUT)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {'a': UUID('184EAB31-4307-416C-AAC4-3B92B2358677')})

    # All validation modes - error - invalid value
    def test_validation_error_invalid_value(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'struct'")
            else:
                self.fail()

    # All validation modes - error - optional none value
    def test_validation_error_optional_none_value(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT, optional=True)

        obj = {'a': None}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value None (type 'NoneType') for member 'a', expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - member validation
    def test_validation_error_member_validation(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)

        obj = {'a': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member 'a', expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - struct with base type member validation
    def test_validation_error_member_validation_base_types(self): # pylint: disable=invalid-name

        base_type = TypeStruct()
        base_type.add_member('a', TYPE_INT)

        type_ = TypeStruct(base_types=[base_type])
        type_.add_member('b', TYPE_STRING)

        obj = {'a': 'abc', 'b': 'def'}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member 'a', expected type 'int'")
            else:
                self.fail()

        obj = {'a': 7, 'b': 8}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 8 (type 'int') for member 'b', expected type 'string'")
            else:
                self.fail()

    # All validation modes - error - nested member validation
    def test_validation_error_nested_member_validation(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type2 = TypeStruct()
        type_.add_member('a', type2)
        type2.add_member('b', TYPE_INT)

        obj = {'a': {'b': 'abc'}}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member 'a.b', expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - unknown member
    def test_validation_error_unknown_member(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)

        obj = {'a': 7, 'b': 8}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Unknown member 'b'")
            else:
                self.fail()

    # All validation modes - error - missing member
    def test_validation_error_missing_member(self): # pylint: disable=invalid-name

        type_ = TypeStruct()
        type_.add_member('a', TYPE_INT)

        obj = {}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Required member 'a' missing")
            else:
                self.fail()

    # All validation modes - error - union with more than one member
    def test_validation_error_union_multiple_members(self): # pylint: disable=invalid-name

        type_ = TypeStruct(union=True)
        type_.add_member('a', TYPE_INT)
        type_.add_member('bb', TYPE_STRING)

        obj = {'a': 1, 'bb': 'abcd'}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertTrue(str(exc).startswith('Invalid value {'))
                self.assertTrue(str(exc).endswith("} (type 'dict'), expected type 'union'"))
            else:
                self.fail()

    # All validation modes - error - empty union
    def test_validation_error_union_zero_members(self): # pylint: disable=invalid-name

        type_ = TypeStruct(union=True)
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING)

        obj = {}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value {} (type 'dict'), expected type 'union'")
            else:
                self.fail()

    # All validation modes - error - union unknown member
    def test_validation_error_union_unknown_member(self): # pylint: disable=invalid-name

        type_ = TypeStruct(union=True)
        type_.add_member('a', TYPE_INT)
        type_.add_member('b', TYPE_STRING)

        obj = {'c': 7}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Unknown member 'c'")
            else:
                self.fail()


class TestModelArrayValidation(unittest.TestCase):

    # Test array type construction
    def test_init(self):

        type_ = TypeArray(TYPE_INT)
        self.assertEqual(type_.type_name, 'array')
        self.assertTrue(isinstance(type_.type, type(TYPE_INT)))
        self.assertEqual(type_.attr, None)

    # All validation modes - success
    def test_validation(self):

        type_ = TypeArray(TYPE_INT)

        obj = [1, 2, 3]
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, list))
            self.assertEqual(obj2, [1, 2, 3])

    # All validation modes - value attributes - success
    def test_validation_attributes(self):

        type_ = TypeArray(TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = [1, 2, 3]
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, list))
            self.assertEqual(obj2, [1, 2, 3])

    # All validation modes - value attributes - invalid value
    def test_validation_attributes_invalid(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = [1, 7, 3]
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7 (type 'int') for member '[1]' [< 5]")
            else:
                self.fail()

    # All validation modes - nested
    def test_validation_nested(self):

        type_ = TypeArray(TypeArray(TYPE_INT))

        obj = [[1, 2, 3], [4, 5, 6]]
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, list))
            self.assertEqual(obj2, [[1, 2, 3], [4, 5, 6]])

    # Query string validation mode - transformed member
    def test_validation_query_string_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_INT)

        obj = [1, '2', 3]
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, [1, 2, 3])

    # Query string validation mode - empty string
    def test_validation_query_string_empty_string(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_INT)

        obj = ''
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, [])

    # JSON input validation mode - transformed member
    def test_validation_json_input_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_UUID)

        obj = ['39E23A29-2BEA-4402-A4D2-BB3DC057D17A']
        obj2 = type_.validate(obj, mode=VALIDATE_JSON_INPUT)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, [UUID('39E23A29-2BEA-4402-A4D2-BB3DC057D17A')])

    # All validation modes - error - invalid value
    def test_validation_error_invalid_value(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_INT)

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'array'")
            else:
                self.fail()

    # All validation modes - error - member validation
    def test_validation_error_member_validation(self): # pylint: disable=invalid-name

        type_ = TypeArray(TYPE_INT)

        obj = [1, 'abc', 3]
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member '[1]', expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - error nested
    def test_validation_error_nested(self):

        type_ = TypeArray(TypeArray(TYPE_INT))

        obj = [[1, 2, 3], [4, 5, 'abc']]
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member '[1][2]', expected type 'int'")
            else:
                self.fail()


class TestModelDictValidation(unittest.TestCase):

    # Test dict type construction
    def test_init(self):

        type_ = TypeDict(TYPE_INT)
        self.assertEqual(type_.type_name, 'dict')
        self.assertTrue(isinstance(type_.type, type(TYPE_INT)))

    # All validation modes - success
    def test_validation(self):

        type_ = TypeDict(TYPE_INT)

        obj = {'a': 7, 'b': 8}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 7, 'b': 8})

    # All validation modes - value attributes - success
    def test_validation_value_attributes(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = {'a': 1, 'b': 2}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 1, 'b': 2})

    # All validation modes - value attributes - invalid value
    def test_validation_value_attributes_invalid(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT, attr=StructMemberAttributes(op_lt=5))

        obj = {'a': 1, 'b': 7}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7 (type 'int') for member 'b' [< 5]")
            else:
                self.fail()

    # All validation modes - key attributes - success
    def test_validation_key_attributes(self):

        type_ = TypeDict(TYPE_INT, key_attr=StructMemberAttributes(op_len_lt=5))

        obj = {'a': 1, 'b': 2}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': 1, 'b': 2})

    # All validation modes - key attributes - invalid key
    def test_validation_key_attributes_invalid(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT, key_attr=StructMemberAttributes(op_len_lt=2))

        obj = {'a': 1, 'bc': 2}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'bc' (type 'str') for member 'bc' [len < 2]")
            else:
                self.fail()

    # All validation modes - nested
    def test_validation_nested(self):

        type_ = TypeDict(TypeDict(TYPE_INT))

        obj = {'a': {'b': 7}}
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, dict))
            self.assertEqual(obj2, {'a': {'b': 7}})

    # Query string validation mode - transformed member
    def test_validation_query_string_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT)

        obj = {'a': '7'}
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {'a': 7})

    # Query string validation mode - empty string
    def test_validation_query_string_empty_string(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT)

        obj = ''
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {})

    # JSON input validation mode - transformed member
    def test_validation_json_input_transformed_member(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_UUID)

        obj = {'a': '72D33C44-7D30-4F15-903C-56DCC6DECD75'}
        obj2 = type_.validate(obj, mode=VALIDATE_JSON_INPUT)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, {'a': UUID('72D33C44-7D30-4F15-903C-56DCC6DECD75')})

    # All validation modes - error - invalid value
    def test_validation_error_invalid_value(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT)

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'dict'")
            else:
                self.fail()

    # All validation modes - error - member key validation
    def test_validation_error_member_key_validation(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT)

        obj = {7: 7}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7 (type 'int') for member '[7]', expected type 'string'")
            else:
                self.fail()

    # All validation modes - error - member validation
    def test_validation_error_member_validation(self): # pylint: disable=invalid-name

        type_ = TypeDict(TYPE_INT)

        obj = {'7': 'abc'}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member '7', expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - nested member validation
    def test_validation_error_nested_member_validation(self): # pylint: disable=invalid-name

        type_ = TypeDict(TypeDict(TYPE_INT))

        obj = {'a': {'b': 'abc'}}
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str') for member 'a.b', expected type 'int'")
            else:
                self.fail()


class TestModelEnumValidation(unittest.TestCase):

    # Test enum type construction
    def test_init(self):

        type_ = TypeEnum()
        type_.add_value('a')
        type_.add_value('b')
        type_values = list(type_.values())

        self.assertEqual(type_.type_name, 'enum')
        self.assertEqual(type_values[0].value, 'a')
        self.assertEqual(type_values[0].doc, [])
        self.assertEqual(type_values[1].value, 'b')
        self.assertEqual(type_values[1].doc, [])
        self.assertEqual(type_.doc, [])

    # Test enum type construction
    def test_base_types(self):

        base_type = TypeEnum()
        base_type.add_value('a')
        base_type.add_value('b')

        base_type2 = TypeEnum()
        base_type2.add_value('a')
        base_type2.add_value('b')

        type_ = TypeEnum(base_types=[base_type, base_type2])
        type_.add_value('e')
        type_.add_value('f')

        self.assertEqual([(v.value, v.doc) for v in type_.values()], [
            ('a', []),
            ('b', []),
            ('a', []),
            ('b', []),
            ('e', []),
            ('f', [])
        ])
        self.assertEqual([(v.value, v.doc) for v in type_.values(include_base_types=False)], [
            ('e', []),
            ('f', [])
        ])

    # All validation modes - valid enumeration value
    def test_validate(self):

        type_ = TypeEnum()
        type_.add_value('a')
        type_.add_value('b')

        obj = 'a'
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - valid enumeration value with base types
    def test_validate_base_types(self):

        base_type = TypeEnum()
        base_type.add_value('a')

        base_type2 = TypeEnum()
        base_type2.add_value('b')

        type_ = TypeEnum(base_types=[base_type, base_type2])
        type_.add_value('c')

        for obj in ('a', 'b', 'c'):
            for mode in ALL_VALIDATION_MODES:
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is obj2)

    # All validation modes - valid enumeration value
    def test_validate_error(self):

        type_ = TypeEnum()
        type_.add_value('a')
        type_.add_value('b')

        obj = 'c'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'c' (type 'str'), expected type 'enum'")
            else:
                self.fail()

    # All validation modes - valid enumeration value
    def test_validate_error_base_types(self):

        base_type = TypeEnum()
        base_type.add_value('a')

        type_ = TypeEnum(base_types=[base_type])
        type_.add_value('b')

        obj = 'c'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'c' (type 'str'), expected type 'enum'")
            else:
                self.fail()


class TestModelStringValidation(unittest.TestCase):

    # Test string type construction
    def test_init(self):

        type_ = TYPE_STRING

        self.assertEqual(type_.type_name, 'string')

    # All validation modes - success
    def test_validate(self):

        type_ = TYPE_STRING

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_STRING

        obj = 7
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7 (type 'int'), expected type 'string'")
            else:
                self.fail()


class TestModelIntValidation(unittest.TestCase):

    # Test int type construction
    def test_init(self):

        type_ = TYPE_INT

        self.assertEqual(type_.type_name, 'int')

    # All validation modes - success
    def test_validate(self):

        type_ = TYPE_INT

        obj = 7
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - float
    def test_validate_float(self):

        type_ = TYPE_INT

        obj = 7.
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, int))
                self.assertEqual(obj2, 7)

    # All validation modes - decimal
    def test_validate_decimal(self):

        type_ = TYPE_INT

        obj = Decimal('7')
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, int))
                self.assertEqual(obj2, 7)

    # Query string validation mode - string
    def test_query_string(self):

        type_ = TYPE_INT

        obj = '7'
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, 7)

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_INT

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - not-integer float
    def test_validate_error_float(self):

        type_ = TYPE_INT

        obj = 7.5
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 7.5 (type 'float'), expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - not-integer decimal
    def test_validate_error_decimal(self):

        type_ = TYPE_INT

        obj = Decimal('7.5')
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value Decimal('7.5') (type 'Decimal'), expected type 'int'")
            else:
                self.fail()

    # All validation modes - error - bool
    def test_validate_error_bool(self):

        type_ = TYPE_INT

        obj = True
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value True (type 'bool'), expected type 'int'")
            else:
                self.fail()


class TestModelFloatValidation(unittest.TestCase):

    # Test float type construction
    def test_init(self):

        type_ = TYPE_FLOAT

        self.assertEqual(type_.type_name, 'float')

    # All validation modes - success
    def test_validate(self):

        type_ = TYPE_FLOAT

        obj = 7.5
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - int
    def test_validate_int(self):

        type_ = TYPE_FLOAT

        obj = 7
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, float))
                self.assertEqual(obj2, 7.)

    # All validation modes - decimal
    def test_validate_decimal(self):

        type_ = TYPE_FLOAT

        obj = Decimal('7.5')
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            if mode in IMMUTABLE_VALIDATION_MODES:
                self.assertTrue(obj is obj2)
            else:
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, float))
                self.assertEqual(obj2, 7.5)

    # Query string validation mode - string
    def test_query_string(self):

        type_ = TYPE_FLOAT

        obj = '7.5'
        obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
        self.assertTrue(obj is not obj2)
        self.assertEqual(obj2, 7.5)

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_FLOAT

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'float'")
            else:
                self.fail()

    # All validation modes - error - invalid value "nan"
    def test_validate_error_nan(self):

        type_ = TYPE_FLOAT

        obj = 'nan'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'nan' (type 'str'), expected type 'float'")
            else:
                self.fail()

    # All validation modes - error - invalid value "inf"
    def test_validate_error_inf(self):

        type_ = TYPE_FLOAT

        obj = 'inf'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'inf' (type 'str'), expected type 'float'")
            else:
                self.fail()

    # All validation modes - error - bool
    def test_validate_error_bool(self):

        type_ = TYPE_FLOAT

        obj = True
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value True (type 'bool'), expected type 'float'")
            else:
                self.fail()


class TestModelBoolValidation(unittest.TestCase):

    # Test bool type construction
    def test_init(self):

        type_ = TYPE_BOOL

        self.assertEqual(type_.type_name, 'bool')

    # Test attribute validation
    def test_validate_attr(self):

        type_ = TYPE_BOOL

        type_.validate_attr(StructMemberAttributes())

        try:
            type_.validate_attr(StructMemberAttributes(op_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute '> 7'")

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - success
    def test_validate(self):

        type_ = TYPE_BOOL

        obj = False
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # Query string validation mode - string
    def test_validate_query_string(self):

        type_ = TYPE_BOOL

        for obj, expected in (('false', False), ('true', True)):
            obj2 = type_.validate(obj, mode=VALIDATE_QUERY_STRING)
            self.assertTrue(obj is not obj2)
            self.assertTrue(isinstance(obj2, bool))
            self.assertEqual(obj2, expected)

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_BOOL

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'bool'")
            else:
                self.fail()


class TestModelUuidValidation(unittest.TestCase):

    # Test uuid type construction
    def test_init(self):

        type_ = TYPE_UUID

        self.assertEqual(type_.type_name, 'uuid')

    # Test attribute validation
    def test_validate_attr(self):

        type_ = TYPE_UUID

        type_.validate_attr(StructMemberAttributes())

        try:
            type_.validate_attr(StructMemberAttributes(op_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute '> 7'")

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - UUID object
    def test_validate(self):

        type_ = TYPE_UUID

        obj = UUID('AED91C7B-DCFD-49B3-A483-DBC9EA2031A3')
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - UUID string
    def test_validate_string(self):

        type_ = TYPE_UUID

        obj = 'AED91C7B-DCFD-49B3-A483-DBC9EA2031A3'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, UUID))
                self.assertEqual(obj2, UUID('AED91C7B-DCFD-49B3-A483-DBC9EA2031A3'))
            else:
                try:
                    obj2 = type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value 'AED91C7B-DCFD-49B3-A483-DBC9EA2031A3' (type 'str'), expected type 'uuid'")
                else:
                    pass

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_UUID

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'uuid'")
            else:
                self.fail()


class TestModelDateValidation(unittest.TestCase):

    # Test date type construction
    def test_init(self):

        type_ = TYPE_DATE

        self.assertEqual(type_.type_name, 'date')

    # Test attribute validation
    def test_validate_attr(self):

        type_ = TYPE_DATE

        type_.validate_attr(StructMemberAttributes())

        try:
            type_.validate_attr(StructMemberAttributes(op_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute '> 7'")

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - date object
    def test_validate(self):

        type_ = TYPE_DATE

        obj = date(2013, 5, 26)
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - ISO date string
    def test_validate_query_string(self):

        type_ = TYPE_DATE

        obj = '2013-05-26'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, date))
                self.assertEqual(obj2, date(2013, 5, 26))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26' (type 'str'), expected type 'date'")
                else:
                    self.fail()

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_DATE

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'date'")
            else:
                self.fail()


class TestModelDatetimeValidation(unittest.TestCase):

    # Test datetime type construction
    def test_init(self):

        type_ = TYPE_DATETIME

        self.assertEqual(type_.type_name, 'datetime')

    # Test attribute validation
    def test_validate_attr(self):

        type_ = TYPE_DATETIME

        type_.validate_attr(StructMemberAttributes())

        try:
            type_.validate_attr(StructMemberAttributes(op_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute '> 7'")

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - datetime object
    def test_validate(self):

        type_ = TYPE_DATETIME

        obj = datetime(2013, 5, 26, 11, 1, 0, tzinfo=TZUTC)
        for mode in ALL_VALIDATION_MODES:
            obj2 = type_.validate(obj, mode)
            self.assertTrue(obj is obj2)

    # All validation modes - datetime object with no timezone
    def test_validate_no_timezone(self):

        type_ = TYPE_DATETIME

        obj = datetime(2013, 5, 26, 11, 1, 0)
        for mode in ALL_VALIDATION_MODES:
            if mode in IMMUTABLE_VALIDATION_MODES:
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is obj2)
            else:
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertEqual(obj2, datetime(2013, 5, 26, 11, 1, 0, tzinfo=TZLOCAL))

    # All validation modes - ISO datetime string
    def test_validate_query_string(self):

        type_ = TYPE_DATETIME

        obj = '2013-05-26T11:01:00+08:00'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, datetime))
                self.assertEqual(obj2, datetime(2013, 5, 26, 3, 1, 0, tzinfo=TZUTC))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26T11:01:00+08:00' (type 'str'), expected type 'datetime'")
                else:
                    self.fail()

    # All validation modes - ISO datetime string - zulu
    def test_validate_query_string_zulu(self):

        type_ = TYPE_DATETIME

        obj = '2013-05-26T11:01:00+00:00'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, datetime))
                self.assertEqual(obj2, datetime(2013, 5, 26, 11, 1, 0, tzinfo=TZUTC))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26T11:01:00+00:00' (type 'str'), expected type 'datetime'")
                else:
                    self.fail()

    # All validation modes - ISO datetime string - fraction second
    def test_validate_query_string_fracsec(self): # pylint: disable=invalid-name

        type_ = TYPE_DATETIME

        obj = '2013-05-26T11:01:00.1234+00:00'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, datetime))
                self.assertEqual(obj2, datetime(2013, 5, 26, 11, 1, 0, 123400, tzinfo=TZUTC))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26T11:01:00.1234+00:00' (type 'str'), expected type 'datetime'")
                else:
                    self.fail()

    # All validation modes - ISO datetime string - no seconds
    def test_validate_query_string_no_seconds(self): # pylint: disable=invalid-name

        type_ = TYPE_DATETIME

        obj = '2013-05-26T11:01Z'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, datetime))
                self.assertEqual(obj2, datetime(2013, 5, 26, 11, 1, 0, 0, tzinfo=TZUTC))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26T11:01Z' (type 'str'), expected type 'datetime'")
                else:
                    self.fail()

    # All validation modes - ISO datetime string - no minutes
    def test_validate_query_string_no_minutes(self): # pylint: disable=invalid-name

        type_ = TYPE_DATETIME

        obj = '2013-05-26T11Z'
        for mode in ALL_VALIDATION_MODES:
            if mode in (VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is not obj2)
                self.assertTrue(isinstance(obj2, datetime))
                self.assertEqual(obj2, datetime(2013, 5, 26, 11, 0, 0, 0, tzinfo=TZUTC))
            else:
                try:
                    type_.validate(obj, mode)
                except ValidationError as exc:
                    self.assertEqual(str(exc), "Invalid value '2013-05-26T11Z' (type 'str'), expected type 'datetime'")
                else:
                    self.fail()

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_DATETIME

        obj = 'abc'
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value 'abc' (type 'str'), expected type 'datetime'")
            else:
                self.fail()


class TestModelObjectValidation(unittest.TestCase):

    # Test object type construction
    def test_init(self):

        type_ = TYPE_OBJECT

        self.assertEqual(type_.type_name, 'object')

    # Test attribute validation
    def test_validate_attr(self):

        type_ = TYPE_OBJECT

        type_.validate_attr(StructMemberAttributes())

        try:
            type_.validate_attr(StructMemberAttributes(op_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute '> 7'")

        try:
            type_.validate_attr(StructMemberAttributes(op_len_gt=7))
            self.fail()
        except AttributeValidationError as exc:
            self.assertEqual(str(exc), "Invalid attribute 'len > 7'")

    # All validation modes - success
    def test_validate(self):

        type_ = TYPE_OBJECT

        for mode in ALL_VALIDATION_MODES:
            for obj in (object(), 'abc', 7, False):
                obj2 = type_.validate(obj, mode)
                self.assertTrue(obj is obj2)

    # All validation modes - error - invalid value
    def test_validate_error(self):

        type_ = TYPE_OBJECT

        obj = None
        for mode in ALL_VALIDATION_MODES:
            try:
                type_.validate(obj, mode)
            except ValidationError as exc:
                self.assertEqual(str(exc), "Invalid value None (type 'NoneType'), expected type 'object'")
            else:
                self.fail()
