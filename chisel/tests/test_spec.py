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

import unittest

from chisel import SpecParser, SpecParserError
from chisel.model import TypeArray, Typedef, TypeDict, TypeEnum, TypeStruct, \
    TYPE_BOOL, TYPE_DATE, TYPE_DATETIME, TYPE_INT, TYPE_FLOAT, TYPE_OBJECT, TYPE_STRING, TYPE_UUID


class TestSpecParseSpec(unittest.TestCase):

    # Helper method to assert struct type member properties
    def assert_struct(self, struct_type, members):
        self.assertTrue(isinstance(struct_type, TypeStruct))
        struct_type_members = list(struct_type.members())
        self.assertEqual(len(struct_type_members), len(members))
        for ix_member in range(0, len(members)):
            if len(members[ix_member]) == 4:
                name, type_, optional, nullable = members[ix_member]
            else:
                name, type_, optional = members[ix_member]
                nullable = False
            self.assertEqual(struct_type_members[ix_member].name, name)
            if isinstance(type_, (TypeStruct, TypeArray, TypeDict, TypeEnum)):
                self.assertTrue(struct_type_members[ix_member].type is type_)
            else:
                self.assertTrue(isinstance(struct_type_members[ix_member].type, type_))
            self.assertEqual(struct_type_members[ix_member].optional, optional)
            self.assertEqual(struct_type_members[ix_member].nullable, nullable)

    # Helper method to assert struct type member properties (by struct name)
    def assert_struct_by_name(self, parser, type_name, members):
        self.assertEqual(parser.types[type_name].type_name, type_name)
        self.assert_struct(parser.types[type_name], members)

    # Helper method to assert enum type values
    def assert_enum(self, enum_type, values):
        self.assertTrue(isinstance(enum_type, TypeEnum))
        self.assertEqual(sum(1 for _ in enum_type.values()), len(values))
        for enum_value in values:
            self.assertTrue(enum_value in enum_type.values())

    # Helper method to assert enum type values (by enum name)
    def assert_enum_by_name(self, parser, type_name, values):
        self.assertEqual(parser.types[type_name].type_name, type_name)
        self.assert_enum(parser.types[type_name], values)

    # Helper method to assert action properties
    def assert_action(self, parser, action_name, input_members, output_members, error_values):
        self.assertEqual(parser.actions[action_name].input_type.type_name, action_name + '_input')
        self.assertEqual(parser.actions[action_name].output_type.type_name, action_name + '_output')
        self.assertEqual(parser.actions[action_name].error_type.type_name, action_name + '_error')
        self.assert_struct(parser.actions[action_name].input_type, input_members)
        self.assert_struct(parser.actions[action_name].output_type, output_members)
        self.assert_enum(parser.actions[action_name].error_type, error_values)

    # Test valid spec parsing
    def test_simple(self):

        # Parse the spec
        parser = SpecParser()
        parser.parse_string('''\
# This is an enum
enum MyEnum
    Foo
    Bar
    "Foo and Bar"

# This is the struct
struct MyStruct

    # The 'a' member
    string a

    # The 'b' member
    int b

# This is the second struct
struct MyStruct2
    int a
    optional \\
        float b
    nullable string \\
        c
    bool d
    int[] e
    optional MyStruct[] f
    optional float{} g
    optional datetime h
    optional uuid i
    optional MyEnum : MyStruct{} j
    optional nullable date k
    optional object l

# This is a union
union MyUnion
    int a
    string b

# The action
action MyAction
    input
        int a
        optional string b
    output
        bool c
    errors
        Error1
        Error2
        "Error 3"

# The second action
action MyAction2
    input
        MyStruct foo
        MyStruct2[] bar

# The third action
action MyAction3
    output
        int a
        datetime b
        date c

# The fourth action
action MyAction4 \\
''')

        # Check errors & counts
        self.assertEqual(len(parser.errors), 0)
        self.assertEqual(len(parser.types), 4)
        self.assertEqual(len(parser.actions), 4)

        # Check enum types
        self.assert_enum_by_name(parser, 'MyEnum',
                                 ('Foo',
                                  'Bar',
                                  'Foo and Bar'))

        # Check struct types
        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('a', type(TYPE_STRING), False),
                                    ('b', type(TYPE_INT), False)))
        self.assert_struct_by_name(parser, 'MyStruct2',
                                   (('a', type(TYPE_INT), False),
                                    ('b', type(TYPE_FLOAT), True),
                                    ('c', type(TYPE_STRING), False, True),
                                    ('d', type(TYPE_BOOL), False),
                                    ('e', TypeArray, False),
                                    ('f', TypeArray, True),
                                    ('g', TypeDict, True),
                                    ('h', type(TYPE_DATETIME), True),
                                    ('i', type(TYPE_UUID), True),
                                    ('j', TypeDict, True),
                                    ('k', type(TYPE_DATE), True, True),
                                    ('l', type(TYPE_OBJECT), True)))
        self.assert_struct_by_name(parser, 'MyUnion',
                                   (('a', type(TYPE_INT), True),
                                    ('b', type(TYPE_STRING), True)))
        mystruct2_members = list(parser.types['MyStruct2'].members())
        self.assertTrue(isinstance(mystruct2_members[4].type.type, type(TYPE_INT)))
        self.assertTrue(isinstance(mystruct2_members[5].type.type, TypeStruct))
        self.assertEqual(mystruct2_members[5].type.type.type_name, 'MyStruct')
        self.assertTrue(isinstance(mystruct2_members[6].type.type, type(TYPE_FLOAT)))
        self.assertTrue(isinstance(mystruct2_members[9].type.type, TypeStruct))
        self.assertTrue(isinstance(mystruct2_members[9].type.key_type, TypeEnum))

        # Check actions
        self.assert_action(parser, 'MyAction',
                           (('a', type(TYPE_INT), False),
                            ('b', type(TYPE_STRING), True)),
                           (('c', type(TYPE_BOOL), False),),
                           ('Error1',
                            'Error2',
                            'Error 3'))
        self.assert_action(parser, 'MyAction2',
                           (('foo', parser.types['MyStruct'], False),
                            ('bar', TypeArray, False)),
                           (),
                           ())
        myaction2_input_members = list(parser.actions['MyAction2'].input_type.members())
        self.assertTrue(isinstance(myaction2_input_members[1].type.type, TypeStruct))
        self.assertEqual(myaction2_input_members[1].type.type.type_name, 'MyStruct2')
        self.assert_action(parser, 'MyAction3',
                           (),
                           (('a', type(TYPE_INT), False),
                            ('b', type(TYPE_DATETIME), False),
                            ('c', type(TYPE_DATE), False)),
                           ())
        self.assert_action(parser, 'MyAction4',
                           (),
                           (),
                           ())

    # Struct with base types
    def test_struct_base_types(self):

        parser = SpecParser(spec='''\
struct MyStruct (MyStruct2)
    int c

struct MyStruct2 (MyStruct3)
    float b

struct MyStruct3
    string a

struct MyStruct4
    bool d

typedef MyStruct4 MyTypedef

struct MyStruct5 (MyStruct2, MyTypedef)
    datetime e
''')

        self.assertEqual(parser.types['MyStruct'].base_types, [parser.types['MyStruct2']])
        self.assertEqual(parser.types['MyStruct2'].base_types, [parser.types['MyStruct3']])
        self.assertEqual(parser.types['MyStruct3'].base_types, None)
        self.assertEqual(parser.types['MyStruct4'].base_types, None)
        self.assertEqual(parser.types['MyStruct5'].base_types, [parser.types['MyStruct2'], parser.types['MyTypedef']])

        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct'].members()
        ], [
            ('a', 'string', False, False, []),
            ('b', 'float', False, False, []),
            ('c', 'int', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct'].members(include_base_types=False)
        ], [
            ('c', 'int', False, False, [])
        ])

        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct2'].members()
        ], [
            ('a', 'string', False, False, []),
            ('b', 'float', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct2'].members(include_base_types=False)
        ], [
            ('b', 'float', False, False, [])
        ])

        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct3'].members()
        ], [
            ('a', 'string', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct3'].members(include_base_types=False)
        ], [
            ('a', 'string', False, False, [])
        ])

        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct4'].members()
        ], [
            ('d', 'bool', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct4'].members(include_base_types=False)
        ], [
            ('d', 'bool', False, False, [])
        ])

        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct5'].members()
        ], [
            ('a', 'string', False, False, []),
            ('b', 'float', False, False, []),
            ('d', 'bool', False, False, []),
            ('e', 'datetime', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc) for m in parser.types['MyStruct5'].members(include_base_types=False)
        ], [
            ('e', 'datetime', False, False, [])
        ])

    # Struct with base types error cases
    def test_struct_base_types_error(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
struct MyStruct (MyEnum)
    int a

enum MyEnum
    A

struct MyStruct3 (MyStruct)
    string a

typedef string{} MyDict

struct MyStruct4
    int b

struct MyStruct5 (MyStruct4, MyDict)
    int b
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":15: error: Invalid struct base type 'MyDict'",
                ":1: error: Invalid struct base type 'MyEnum'",
                ":7: error: Redefinition of member 'a' from base type",
                ":15: error: Redefinition of member 'b' from base type"
            ])
        else:
            self.fail()

    # Struct with circular base types error case
    def test_struct_base_types_circular(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
struct MyStruct (MyStruct2)
    int a

struct MyStruct2 (MyStruct3)
    int b

struct MyStruct3 (MyStruct)
    int c
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":1: error: Circular base type detected for type 'MyStruct2'",
                ":4: error: Circular base type detected for type 'MyStruct3'",
                ":7: error: Circular base type detected for type 'MyStruct'"
            ])
        else:
            self.fail()

    # Enum with base types
    def test_enum_base_types(self):

        parser = SpecParser(spec='''\
enum MyEnum (MyEnum2)
    c

enum MyEnum2 (MyEnum3)
    b

enum MyEnum3
    a

enum MyEnum4
    d

typedef MyEnum4 MyTypedef

enum MyEnum5 (MyEnum2, MyTypedef)
    e
''')

        self.assertEqual(parser.types['MyEnum'].base_types, [parser.types['MyEnum2']])
        self.assertEqual(parser.types['MyEnum2'].base_types, [parser.types['MyEnum3']])
        self.assertEqual(parser.types['MyEnum3'].base_types, None)
        self.assertEqual(parser.types['MyEnum4'].base_types, None)
        self.assertEqual(parser.types['MyEnum5'].base_types, [parser.types['MyEnum2'], parser.types['MyTypedef']])

        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum'].values()
        ], [
            ('a', []),
            ('b', []),
            ('c', [])
        ])
        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum'].values(include_base_types=False)
        ], [
            ('c', [])
        ])

        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum2'].values()
        ], [
            ('a', []),
            ('b', [])
        ])
        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum2'].values(include_base_types=False)
        ], [
            ('b', [])
        ])

        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum3'].values()
        ], [
            ('a', [])
        ])
        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum3'].values(include_base_types=False)
        ], [
            ('a', [])
        ])

        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum4'].values()
        ], [
            ('d', [])
        ])
        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum4'].values(include_base_types=False)
        ], [
            ('d', [])
        ])

        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum5'].values()
        ], [
            ('a', []),
            ('b', []),
            ('d', []),
            ('e', [])
        ])
        self.assertEqual([
            (v.value, v.doc) for v in parser.types['MyEnum5'].values(include_base_types=False)
        ], [
            ('e', [])
        ])

    # Enum with base types error cases
    def test_enum_base_types_error(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
enum MyEnum (MyStruct)
    A

struct MyStruct
    int a

enum MyEnum3 (MyEnum)
    A

typedef string{} MyDict

enum MyEnum4
    B

enum MyEnum5 (MyEnum4, MyDict)
    B
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":15: error: Invalid enum base type 'MyDict'",
                ":1: error: Invalid enum base type 'MyStruct'",
                ":7: error: Redefinition of enumeration value 'A' from base type",
                ":15: error: Redefinition of enumeration value 'B' from base type"
            ])
        else:
            self.fail()

    # Enum with circular base types error case
    def test_enum_base_types_circular(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
enum MyEnum (MyEnum2)
    a

enum MyEnum2 (MyEnum3)
    b

enum MyEnum3 (MyEnum)
    c
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":1: error: Circular base type detected for type 'MyEnum2'",
                ":4: error: Circular base type detected for type 'MyEnum3'",
                ":7: error: Circular base type detected for type 'MyEnum'"
            ])
        else:
            self.fail()

    # Test multiple parse calls per parser instance
    def test_multiple(self):

        # Parse spec strings
        parser = SpecParser()
        parser.parse_string('''\
enum MyEnum
    A
    B

action MyAction
    input
        MyStruct2 a
    output
        MyStruct b
        MyEnum2 c

struct MyStruct
    string c
    MyEnum2 d
    MyStruct2 e
''', finalize=False)
        parser.parse_string('''\
action MyAction2
    input
        MyStruct d
    output
        MyStruct2 e

struct MyStruct2
    string f
    MyEnum2 g

enum MyEnum2
    C
    D
''')

        # Check errors & counts
        self.assertEqual(len(parser.errors), 0)
        self.assertEqual(len(parser.types), 4)
        self.assertEqual(len(parser.actions), 2)

        # Check enum types
        self.assert_enum_by_name(parser, 'MyEnum',
                                 ('A',
                                  'B'))
        self.assert_enum_by_name(parser, 'MyEnum2',
                                 ('C',
                                  'D'))

        # Check struct types
        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('c', type(TYPE_STRING), False),
                                    ('d', parser.types['MyEnum2'], False),
                                    ('e', parser.types['MyStruct2'], False)))
        self.assert_struct_by_name(parser, 'MyStruct2',
                                   (('f', type(TYPE_STRING), False),
                                    ('g', parser.types['MyEnum2'], False)))

        # Check actions
        self.assert_action(parser, 'MyAction',
                           (('a', TypeStruct, False),),
                           (('b', TypeStruct, False),
                            ('c', parser.types['MyEnum2'], False)),
                           ())
        myaction_input_members = list(parser.actions['MyAction'].input_type.members())
        myaction_output_members = list(parser.actions['MyAction'].output_type.members())
        self.assertEqual(myaction_input_members[0].type.type_name, 'MyStruct2')
        self.assertEqual(myaction_output_members[0].type.type_name, 'MyStruct')
        self.assert_action(parser, 'MyAction2',
                           (('d', TypeStruct, False),),
                           (('e', TypeStruct, False),),
                           ())
        myaction2_input_members = list(parser.actions['MyAction2'].input_type.members())
        myaction2_output_members = list(parser.actions['MyAction2'].output_type.members())
        self.assertEqual(myaction2_input_members[0].type.type_name, 'MyStruct')
        self.assertEqual(myaction2_output_members[0].type.type_name, 'MyStruct2')

    # Test multiple finalize
    def test_multiple_finalize(self):

        # Parse spec strings
        parser = SpecParser()
        parser.parse_string('''\
struct MyStruct
    MyEnum a

enum MyEnum
    A
    B
''')
        parser.parse_string('''\
struct MyStruct2
    int a
    MyEnum b
    MyEnum2 c

enum MyEnum2
    C
    D
''')

        # Check enum types
        self.assert_enum_by_name(parser, 'MyEnum',
                                 ('A',
                                  'B'))
        self.assert_enum_by_name(parser, 'MyEnum2',
                                 ('C',
                                  'D'))

        # Check struct types
        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('a', parser.types['MyEnum'], False),))
        self.assert_struct_by_name(parser, 'MyStruct2',
                                   (('a', type(TYPE_INT), False),
                                    ('b', parser.types['MyEnum'], False),
                                    ('c', parser.types['MyEnum2'], False)))

    def test_typeref_array_attr(self):

        parser = SpecParser()
        parser.parse_string('''\
struct MyStruct
    MyStruct2[len > 0] a
struct MyStruct2
''')

        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('a', TypeArray, False),))
        mystruct_members = list(parser.types['MyStruct'].members())
        self.assertTrue(mystruct_members[0].type.type is parser.types['MyStruct2'])
        self.assertTrue(mystruct_members[0].type.attr is None)
        self.assertTrue(mystruct_members[0].attr is not None)

        self.assert_struct_by_name(parser, 'MyStruct2', ())

    def test_typeref_dict_attr(self):

        parser = SpecParser()
        parser.parse_string('''\
struct MyStruct
    MyEnum : MyStruct2{len > 0} a
enum MyEnum
struct MyStruct2
''')

        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('a', TypeDict, False),))
        mystruct_members = list(parser.types['MyStruct'].members())
        self.assertTrue(mystruct_members[0].type.type is parser.types['MyStruct2'])
        self.assertTrue(mystruct_members[0].type.attr is None)
        self.assertTrue(mystruct_members[0].type.key_type is parser.types['MyEnum'])
        self.assertTrue(mystruct_members[0].type.key_attr is None)
        self.assertTrue(mystruct_members[0].attr is not None)

        self.assert_struct_by_name(parser, 'MyStruct2', ())

    def test_typeref_invalid_nullable_order(self): # pylint: disable=invalid-name

        parser = SpecParser()
        try:
            parser.parse_string('''\
struct MyStruct
    nullable optional int a
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), """\
:2: error: Syntax error""")
        else:
            self.fail()

    def test_typeref_invalid_attr(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
struct MyStruct
    MyStruct2(len > 0) a
struct MyStruct2
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), """\
:2: error: Invalid attribute 'len > 0'""")
        else:
            self.fail()

    # Test members referencing unknown user types
    def test_error_unknown_type(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
struct Foo
    MyBadType a

action MyAction
    input
        MyBadType2 a
    output
        MyBadType b
''', filename='foo')
        except SpecParserError as exc:
            self.assertEqual(str(exc), """\
foo:2: error: Unknown member type 'MyBadType'
foo:6: error: Unknown member type 'MyBadType2'
foo:8: error: Unknown member type 'MyBadType'""")
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 3)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 1)

        # Check errors
        self.assertEqual(parser.errors,
                         ["foo:2: error: Unknown member type 'MyBadType'",
                          "foo:6: error: Unknown member type 'MyBadType2'",
                          "foo:8: error: Unknown member type 'MyBadType'"])

    # Error - redefinition of struct
    def test_error_struct_redefinition(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
struct Foo
    int a

enum Foo
    A
    B
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), ":4: error: Redefinition of type 'Foo'")
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 1)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 0)

        # Check types
        self.assert_enum_by_name(parser, 'Foo', ('A', 'B'))

        # Check errors
        self.assertEqual(parser.errors,
                         [":4: error: Redefinition of type 'Foo'"])

    # Error - redefinition of enum
    def test_error_enum_redefinition(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
enum Foo
    A
    B

struct Foo
    int a
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), ":5: error: Redefinition of type 'Foo'")
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 1)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 0)

        # Check types
        self.assert_struct_by_name(parser, 'Foo',
                                   (('a', type(TYPE_INT), False),))

        # Check errors
        self.assertEqual(parser.errors,
                         [":5: error: Redefinition of type 'Foo'"])

    # Error - redefinition of typedef
    def test_error_typedef_redefinition(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
struct Foo
    int a

typedef int(> 5) Foo
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), ":4: error: Redefinition of type 'Foo'")
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 1)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 0)

        # Check types
        typedef = parser.types['Foo']
        self.assertTrue(isinstance(typedef, Typedef))
        self.assertEqual(typedef.type_name, 'Foo')
        self.assertEqual(typedef.doc, [])
        self.assertTrue(isinstance(typedef.type, type(TYPE_INT)))
        self.assertEqual(self.attr_tuple(typedef.attr), self.attr_tuple(op_gt=5))

        # Check errors
        self.assertEqual(parser.errors,
                         [":4: error: Redefinition of type 'Foo'"])

    # Error - redefinition of user type
    def test_error_action_redefinition(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
action MyAction
    input
        int a

action MyAction
    input
        string b
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), ":5: error: Redefinition of action 'MyAction'")
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 1)
        self.assertEqual(len(parser.types), 0)
        self.assertEqual(len(parser.actions), 1)

        # Check actions
        self.assert_action(parser, 'MyAction',
                           (('b', type(TYPE_STRING), False),),
                           (),
                           ())

        # Check errors
        self.assertEqual(parser.errors,
                         [":5: error: Redefinition of action 'MyAction'"])

    # Error - invalid action section usage
    def test_error_action_section(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
action MyAction

struct MyStruct
    int a

    input
    output
    errors

input
output
errors
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), '''\
:6: error: Action section outside of action scope
:7: error: Action section outside of action scope
:8: error: Action section outside of action scope
:10: error: Syntax error
:11: error: Syntax error
:12: error: Syntax error''')
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 6)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 1)

        # Check types
        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('a', type(TYPE_INT), False),))

        # Check actions
        self.assert_action(parser, 'MyAction', (), (), ())

        # Check errors
        self.assertEqual(parser.errors,
                         [':6: error: Action section outside of action scope',
                          ':7: error: Action section outside of action scope',
                          ':8: error: Action section outside of action scope',
                          ':10: error: Syntax error',
                          ':11: error: Syntax error',
                          ':12: error: Syntax error'])

    # Error - member definition outside struct scope
    def test_error_member(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
action MyAction
    int abc

struct MyStruct

enum MyEnum

    int bcd

int cde
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), '''\
:2: error: Member definition outside of struct scope
:8: error: Member definition outside of struct scope
:10: error: Syntax error''')
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 3)
        self.assertEqual(len(parser.types), 2)
        self.assertEqual(len(parser.actions), 1)

        # Check types
        self.assert_struct_by_name(parser, 'MyStruct', ())
        self.assert_enum_by_name(parser, 'MyEnum', ())

        # Check actions
        self.assert_action(parser, 'MyAction', (), (), ())

        # Check errors
        self.assertEqual(parser.errors,
                         [':2: error: Member definition outside of struct scope',
                          ':8: error: Member definition outside of struct scope',
                          ':10: error: Syntax error'])

    # Error - enum value definition outside enum scope
    def test_error_enum(self):

        # Parse spec string
        parser = SpecParser()
        try:
            parser.parse_string('''\
enum MyEnum
    "abc
    abc"
Value1

struct MyStruct

    Value2

action MyAction
    input
        MyError
''')
        except SpecParserError as exc:
            self.assertEqual(str(exc), '''\
:2: error: Syntax error
:3: error: Syntax error
:4: error: Syntax error
:8: error: Enumeration value outside of enum scope
:12: error: Enumeration value outside of enum scope''')
        else:
            self.fail()

        # Check counts
        self.assertEqual(len(parser.errors), 5)
        self.assertEqual(len(parser.types), 2)
        self.assertEqual(len(parser.actions), 1)

        # Check types
        self.assert_struct_by_name(parser, 'MyStruct', ())
        self.assert_enum_by_name(parser, 'MyEnum', ())

        # Check actions
        self.assert_action(parser, 'MyAction', (), (), ())

        # Check errors
        self.assertEqual(parser.errors,
                         [':2: error: Syntax error',
                          ':3: error: Syntax error',
                          ':4: error: Syntax error',
                          ':8: error: Enumeration value outside of enum scope',
                          ':12: error: Enumeration value outside of enum scope'])

    @staticmethod
    def attr_tuple(attr=None, op_eq=None, op_lt=None, op_lte=None, op_gt=None, op_gte=None,
                   op_len_eq=None, op_len_lt=None, op_len_lte=None, op_len_gt=None, op_len_gte=None):
        return (attr.op_eq if attr else op_eq,
                attr.op_lt if attr else op_lt,
                attr.op_lte if attr else op_lte,
                attr.op_gt if attr else op_gt,
                attr.op_gte if attr else op_gte,
                attr.op_len_eq if attr else op_len_eq,
                attr.op_len_lt if attr else op_len_lt,
                attr.op_len_lte if attr else op_len_lte,
                attr.op_len_gt if attr else op_len_gt,
                attr.op_len_gte if attr else op_len_gte)

    # Test valid attribute usage
    def test_attributes(self):

        # Parse spec string
        parser = SpecParser()
        parser.parse_string('''\
struct MyStruct
    optional int(> 1,<= 10.5) i1
    optional int (>= 1, < 10 ) i2
    int( > 0, <= 10) i3
    int(> -4, < -1.4) i4
    int(== 5) i5
    float( > 1, <= 10.5) f1
    float(>= 1.5, < 10 ) f2
    string(len > 5, len < 101) s1
    string( len >= 5, len <= 100 ) s2
    string( len == 2 ) s3
    int(> 5)[] ai1
    string(len < 5)[len < 10] as1
    string(len == 2)[len == 3] as2
    int(< 15){} di1
    string(len > 5){len > 10} ds1
    string(len == 2){len == 3} ds2
    string(len == 1) : string(len == 2){len == 3} ds3
''', filename='foo')
        struct = parser.types['MyStruct']

        # Check counts
        self.assertEqual(len(parser.errors), 0)
        self.assertEqual(len(parser.types), 1)
        self.assertEqual(len(parser.actions), 0)

        # Check struct members
        self.assert_struct_by_name(parser, 'MyStruct',
                                   (('i1', type(TYPE_INT), True),
                                    ('i2', type(TYPE_INT), True),
                                    ('i3', type(TYPE_INT), False),
                                    ('i4', type(TYPE_INT), False),
                                    ('i5', type(TYPE_INT), False),
                                    ('f1', type(TYPE_FLOAT), False),
                                    ('f2', type(TYPE_FLOAT), False),
                                    ('s1', type(TYPE_STRING), False),
                                    ('s2', type(TYPE_STRING), False),
                                    ('s3', type(TYPE_STRING), False),
                                    ('ai1', TypeArray, False),
                                    ('as1', TypeArray, False),
                                    ('as2', TypeArray, False),
                                    ('di1', TypeDict, False),
                                    ('ds1', TypeDict, False),
                                    ('ds2', TypeDict, False),
                                    ('ds3', TypeDict, False),
                                   ))

        # Check i1 constraints
        itm = iter(struct.members())
        struct_i1 = next(itm)
        self.assertEqual(self.attr_tuple(struct_i1.attr), self.attr_tuple(op_lte=10.5, op_gt=1))

        # Check i2 constraints
        struct_i2 = next(itm)
        self.assertEqual(self.attr_tuple(struct_i2.attr), self.attr_tuple(op_lt=10, op_gte=1))

        # Check i3 constraints
        struct_i3 = next(itm)
        self.assertEqual(self.attr_tuple(struct_i3.attr), self.attr_tuple(op_lte=10, op_gt=0))

        # Check i4 constraints
        struct_i4 = next(itm)
        self.assertEqual(self.attr_tuple(struct_i4.attr), self.attr_tuple(op_lt=-1.4, op_gt=-4))

        # Check i5 constraints
        struct_i5 = next(itm)
        self.assertEqual(self.attr_tuple(struct_i5.attr), self.attr_tuple(op_eq=5))

        # Check f1 constraints
        struct_f1 = next(itm)
        self.assertEqual(self.attr_tuple(struct_f1.attr), self.attr_tuple(op_lte=10.5, op_gt=1))

        # Check f2 constraints
        struct_f2 = next(itm)
        self.assertEqual(self.attr_tuple(struct_f2.attr), self.attr_tuple(op_lt=10, op_gte=1.5))

        # Check s1 constraints
        struct_s1 = next(itm)
        self.assertEqual(self.attr_tuple(struct_s1.attr), self.attr_tuple(op_len_lt=101, op_len_gt=5))

        # Check s2 constraints
        struct_s2 = next(itm)
        self.assertEqual(self.attr_tuple(struct_s2.attr), self.attr_tuple(op_len_lte=100, op_len_gte=5))

        # Check s3 constraints
        struct_s3 = next(itm)
        self.assertEqual(self.attr_tuple(struct_s3.attr), self.attr_tuple(op_len_eq=2))

        # Check ai1 constraints
        struct_ai1 = next(itm)
        self.assertEqual(struct_ai1.attr, None)
        self.assertEqual(self.attr_tuple(struct_ai1.type.attr), self.attr_tuple(op_gt=5))

        # Check as1 constraints
        struct_as1 = next(itm)
        self.assertEqual(self.attr_tuple(struct_as1.attr), self.attr_tuple(op_len_lt=10))
        self.assertEqual(self.attr_tuple(struct_as1.type.attr), self.attr_tuple(op_len_lt=5))

        # Check as2 constraints
        struct_as2 = next(itm)
        self.assertEqual(self.attr_tuple(struct_as2.attr), self.attr_tuple(op_len_eq=3))
        self.assertEqual(self.attr_tuple(struct_as2.type.attr), self.attr_tuple(op_len_eq=2))

        # Check di1 constraints
        struct_di1 = next(itm)
        self.assertEqual(struct_di1.attr, None)
        self.assertEqual(self.attr_tuple(struct_di1.type.attr), self.attr_tuple(op_lt=15))

        # Check ds1 constraints
        struct_ds1 = next(itm)
        self.assertEqual(self.attr_tuple(struct_ds1.attr), self.attr_tuple(op_len_gt=10))
        self.assertEqual(self.attr_tuple(struct_ds1.type.attr), self.attr_tuple(op_len_gt=5))

        # Check ds2 constraints
        ds2 = next(itm)
        self.assertEqual(self.attr_tuple(ds2.attr), self.attr_tuple(op_len_eq=3))
        self.assertEqual(self.attr_tuple(ds2.type.attr), self.attr_tuple(op_len_eq=2))

        # Check ds3 constraints
        ds3 = next(itm)
        self.assertEqual(self.attr_tuple(ds3.attr), self.attr_tuple(op_len_eq=3))
        self.assertEqual(self.attr_tuple(ds3.type.attr), self.attr_tuple(op_len_eq=2))
        self.assertEqual(self.attr_tuple(ds3.type.key_attr), self.attr_tuple(op_len_eq=1))

        self.assertEqual(next(itm, None), None)

    def _test_spec_error(self, errors, spec):
        parser = SpecParser()
        try:
            parser.parse_string(spec)
        except SpecParserError as exc:
            self.assertEqual(str(exc), '\n'.join(errors))
        else:
            self.fail()
        self.assertEqual(len(parser.errors), len(errors))
        self.assertEqual(parser.errors, errors)

    def test_error_attribute_eq(self):
        self._test_spec_error([":2: error: Invalid attribute '== 7'"], '''\
struct MyStruct
    string(== 7) s
''')

    def test_error_attribute_lt(self):
        self._test_spec_error([":2: error: Invalid attribute '< 7'"], '''\
struct MyStruct
    string(< 7) s
''')

    def test_error_attribute_gt(self):
        self._test_spec_error([":2: error: Invalid attribute '> 7'"], '''\
struct MyStruct
    string(> 7) s
''')

    def test_error_attribute_lt_gt(self):
        self._test_spec_error([":2: error: Invalid attribute '< 7'"], '''\
struct MyStruct
    string(< 7, > 7) s
''')

    def test_error_attribute_lte_gte(self):
        self._test_spec_error([":6: error: Invalid attribute '>= 1'",
                               ":7: error: Invalid attribute '<= 2'"], '''\
enum MyEnum
    Foo
    Bar

struct MyStruct
    MyStruct(>= 1) a
    MyEnum(<= 2) b
''')

    def test_error_attribute_len_eq(self):
        self._test_spec_error([":2: error: Invalid attribute 'len == 1'"], '''\
struct MyStruct
    int(len == 1) i
''')

    def test_error_attribute_len_lt(self):
        self._test_spec_error([":2: error: Invalid attribute 'len < 10'"], '''\
struct MyStruct
    float(len < 10) f
''')

    def test_error_attribute_len_gt(self):
        self._test_spec_error([":2: error: Invalid attribute 'len > 1'"], '''\
struct MyStruct
    int(len > 1) i
''')

    def test_error_attribute_len_lt_gt(self):
        self._test_spec_error([":2: error: Invalid attribute 'len < 10'"], '''\
struct MyStruct
    float(len < 10, len > 10) f
''')

    def test_error_attribute_len_lte_gte(self): # pylint: disable=invalid-name
        self._test_spec_error([":2: error: Invalid attribute 'len <= 10'",
                               ":3: error: Invalid attribute 'len >= 10'"], '''\
struct MyStruct
    float(len <= 10) f
    float(len >= 10) f2
''')

    def test_error_attribute_invalid(self):
        self._test_spec_error([':2: error: Syntax error'], '''\
struct MyStruct
    string(regex="abc") a
''')

    def test_error_member_invalid(self):
        self._test_spec_error([':1: error: Member definition outside of struct scope',
                               ':5: error: Member definition outside of struct scope'], '''\
    string a

enum MyEnum
    Foo
    int b
''')

    def test_error_member_redefinition(self):
        self._test_spec_error([":4: error: Redefinition of member 'b'"], '''\
struct MyStruct
    string b
    int a
    float b
''')

    def test_error_enum_duplicate_value(self):
        self._test_spec_error([":4: error: Redefinition of enumeration value 'bar'"], '''\
enum MyEnum
    bar
    foo
    bar
''')

    def test_doc(self):

        # Parse spec string
        parser = SpecParser()
        parser.parse_string('''\
# My enum
enum MyEnum

  # MyEnum value 1
  MyEnumValue1

  #
  # MyEnum value 2
  #
  # Second line
  #
  MyEnumValue2

#- Hidden comment
enum MyEnum2

  #- Hidden comment
  MyEnum2Value1

# My struct
struct MyStruct

  # MyStruct member a
  int a

  #
  # MyStruct member b
  #
  string[] b

#- Hidden comment
struct MyStruct2

  #- Hidden comment
  int a

# My action
action MyAction

  input

    # My input member
    float a

  output

    # My output member
    datetime b
''')
        self.assertEqual(len(parser.errors), 0)

        # Check documentation comments
        self.assertEqual(parser.types['MyEnum'].doc,
                         ['My enum'])
        myenum_values = list(parser.types['MyEnum'].values())
        self.assertEqual(myenum_values[0].doc,
                         ['MyEnum value 1'])
        self.assertEqual(myenum_values[1].doc,
                         ['', 'MyEnum value 2', '', 'Second line', ''])
        self.assertEqual(parser.types['MyEnum2'].doc,
                         [])
        myenum2_values = list(parser.types['MyEnum2'].values())
        self.assertEqual(myenum2_values[0].doc,
                         [])
        self.assertEqual(parser.types['MyStruct'].doc,
                         ['My struct'])
        mystruct_members = list(parser.types['MyStruct'].members())
        self.assertEqual(mystruct_members[0].doc,
                         ['MyStruct member a'])
        self.assertEqual(mystruct_members[1].doc,
                         ['', 'MyStruct member b', ''])
        self.assertEqual(parser.types['MyStruct2'].doc,
                         [])
        mystruct2_members = list(parser.types['MyStruct2'].members())
        self.assertEqual(mystruct2_members[0].doc,
                         [])
        self.assertEqual(parser.actions['MyAction'].doc,
                         ['My action'])
        self.assertEqual(parser.actions['MyAction'].input_type.doc,
                         [])
        myaction_input_members = list(parser.actions['MyAction'].input_type.members())
        myaction_output_members = list(parser.actions['MyAction'].output_type.members())
        self.assertEqual(myaction_input_members[0].doc,
                         ['My input member'])
        self.assertEqual(parser.actions['MyAction'].output_type.doc,
                         [])
        self.assertEqual(myaction_output_members[0].doc,
                         ['My output member'])

    def test_typedef(self):

        parser = SpecParser()
        parser.parse_string('''\
typedef MyEnum MyTypedef2

enum MyEnum
    A
    B

# My typedef
typedef MyEnum : MyStruct{len > 0} MyTypedef

struct MyStruct
    int a
    optional int b
''')

        self.assertEqual(len(parser.types), 4)

        typedef = parser.types['MyTypedef']
        self.assertTrue(isinstance(typedef, Typedef))
        self.assertEqual(typedef.type_name, 'MyTypedef')
        self.assertEqual(typedef.doc, ['My typedef'])
        self.assertTrue(isinstance(typedef.type, TypeDict))
        self.assertEqual(self.attr_tuple(typedef.attr), self.attr_tuple(op_len_gt=0))
        self.assertTrue(typedef.type.key_type is parser.types['MyEnum'])
        self.assertEqual(typedef.type.key_type.doc, [])
        self.assertEqual(sum(1 for _ in typedef.type.key_type.values()), 2)
        self.assertTrue(typedef.type.type is parser.types['MyStruct'])
        self.assertEqual(typedef.type.type.doc, [])
        self.assertEqual(sum(1 for _ in typedef.type.type.members()), 2)

        typedef2 = parser.types['MyTypedef2']

        self.assertTrue(isinstance(typedef2, Typedef))
        self.assertEqual(typedef2.type_name, 'MyTypedef2')
        self.assertEqual(typedef2.doc, [])
        self.assertTrue(typedef2.type is parser.types['MyEnum'])
        self.assertEqual(typedef2.attr, None)

    def test_error_dict_non_string_key(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
struct Foo
    int : int {} a
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ':2: error: Invalid dictionary key type',
            ])
        else:
            self.fail()

    def test_error_action_input_redefinition(self): # pylint: disable=invalid-name

        parser = SpecParser()
        try:
            parser.parse_string('''\
action Foo
    input
        int a
    output
        int b
    input
        int c
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ':6: error: Redefinition of action input',
                ':7: error: Member definition outside of struct scope',
            ])
        else:
            self.fail()

    def test_error_action_output_redefinition(self): # pylint: disable=invalid-name

        parser = SpecParser()
        try:
            parser.parse_string('''\
action Foo
    output
        int a
    input
        int b
    output
        int c
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ':6: error: Redefinition of action output',
                ':7: error: Member definition outside of struct scope',
            ])
        else:
            self.fail()

    def test_error_action_errors_redefinition(self): # pylint: disable=invalid-name

        parser = SpecParser()
        try:
            parser.parse_string('''\
action Foo
    errors
        A
        B
    input
        int a
    errors
        C
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ':7: error: Redefinition of action errors',
                ':8: error: Enumeration value outside of enum scope',
            ])
        else:
            self.fail()

    def test_action_input_base_types(self):

        parser = SpecParser()
        parser.parse_string('''\
struct Foo
    int a
    optional string b

struct Bonk
    nullable float c

typedef Bonk Bar

action FooAction
    input (Foo)
        bool c

action BarAction
    input (Foo, Bar)
        datetime d
''')

        self.assertEqual(parser.actions['FooAction'].input_type.base_types, [parser.types['Foo']])
        self.assertEqual(parser.actions['FooAction'].output_type.base_types, None)
        self.assertEqual(parser.actions['FooAction'].error_type.base_types, None)
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['FooAction'].input_type.members()
        ], [
            ('a', 'int', False, False, []),
            ('b', 'string', True, False, []),
            ('c', 'bool', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['FooAction'].input_type.members(include_base_types=False)
        ], [
            ('c', 'bool', False, False, [])
        ])
        self.assertEqual(list(parser.actions['FooAction'].output_type.members()), [])
        self.assertEqual(list(parser.actions['FooAction'].error_type.values()), [])

        self.assertEqual(parser.actions['BarAction'].input_type.base_types, [parser.types['Foo'], parser.types['Bar']])
        self.assertEqual(parser.actions['BarAction'].output_type.base_types, None)
        self.assertEqual(parser.actions['BarAction'].error_type.base_types, None)
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['BarAction'].input_type.members()
        ], [
            ('a', 'int', False, False, []),
            ('b', 'string', True, False, []),
            ('c', 'float', False, True, []),
            ('d', 'datetime', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['BarAction'].input_type.members(include_base_types=False)
        ], [
            ('d', 'datetime', False, False, [])
        ])
        self.assertEqual(list(parser.actions['BarAction'].output_type.members()), [])
        self.assertEqual(list(parser.actions['BarAction'].error_type.values()), [])

    def test_action_input_non_struct(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
action FooAction
    input (Foo)
        #- will not error
        float a

enum Foo
    A
    B

struct MyStruct
    int a

action BarAction
    input (Foo, MyStruct)

union MyUnion

action BonkAction
    input (MyStruct, MyUnion)
        float a

typedef string{} MyDict

action MyDictAction
    input (MyDict)
        int a
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":14: error: Invalid action input base type 'Foo'",
                ":19: error: Invalid action input base type 'MyUnion'",
                ":25: error: Invalid action input base type 'MyDict'",
                ":2: error: Invalid action input base type 'Foo'",
                ":19: error: Redefinition of member 'a' from base type"
            ])
        else:
            self.fail()

    def test_action_output_struct(self):

        parser = SpecParser()
        parser.parse_string('''\
struct Foo
    int a
    optional string b

struct Bonk
    nullable float c

typedef Bonk Bar

action FooAction
    output (Foo)
        bool c

action BarAction
    output (Foo, Bar)
        datetime d
''')

        self.assertEqual(parser.actions['FooAction'].input_type.base_types, None)
        self.assertEqual(parser.actions['FooAction'].output_type.base_types, [parser.types['Foo']])
        self.assertEqual(parser.actions['FooAction'].error_type.base_types, None)
        self.assertEqual(list(parser.actions['FooAction'].input_type.members()), [])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['FooAction'].output_type.members()
        ], [
            ('a', 'int', False, False, []),
            ('b', 'string', True, False, []),
            ('c', 'bool', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['FooAction'].output_type.members(include_base_types=False)
        ], [
            ('c', 'bool', False, False, [])
        ])
        self.assertEqual(list(parser.actions['FooAction'].error_type.values()), [])

        self.assertEqual(parser.actions['BarAction'].input_type.base_types, None)
        self.assertEqual(parser.actions['BarAction'].output_type.base_types, [parser.types['Foo'], parser.types['Bar']])
        self.assertEqual(parser.actions['BarAction'].error_type.base_types, None)
        self.assertEqual(list(parser.actions['BarAction'].input_type.members()), [])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['BarAction'].output_type.members()
        ], [
            ('a', 'int', False, False, []),
            ('b', 'string', True, False, []),
            ('c', 'float', False, True, []),
            ('d', 'datetime', False, False, [])
        ])
        self.assertEqual([
            (m.name, m.type.type_name, m.optional, m.nullable, m.doc)
            for m in parser.actions['BarAction'].output_type.members(include_base_types=False)
        ], [
            ('d', 'datetime', False, False, [])
        ])
        self.assertEqual(list(parser.actions['BarAction'].error_type.values()), [])

    def test_action_output_non_struct(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
action FooAction
    output (Foo)
        #- will not error
        float a

enum Foo
    A
    B

struct MyStruct
    int a

action BarAction
    output (Foo, MyStruct)

union MyUnion

action BonkAction
    output (MyStruct, MyUnion)
        float a

typedef string{} MyDict

action MyDictAction
    output (MyDict)
        #- will not error
        int a
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":14: error: Invalid action output base type 'Foo'",
                ":19: error: Invalid action output base type 'MyUnion'",
                ":25: error: Invalid action output base type 'MyDict'",
                ":2: error: Invalid action output base type 'Foo'",
                ":19: error: Redefinition of member 'a' from base type"
            ])
        else:
            self.fail()

    def test_action_errors_enum(self):

        parser = SpecParser()
        parser.parse_string('''\
action FooAction
    errors (Foo)
        C

enum Foo
    A
    B

enum Bonk
    C

typedef Bonk Bar

action BarAction
    errors (Foo, Bar)
        D
''')

        self.assertEqual(parser.actions['FooAction'].input_type.base_types, None)
        self.assertEqual(parser.actions['FooAction'].output_type.base_types, None)
        self.assertEqual(parser.actions['FooAction'].error_type.base_types, [parser.types['Foo']])
        self.assertEqual(list(parser.actions['FooAction'].input_type.members()), [])
        self.assertEqual(list(parser.actions['FooAction'].output_type.members()), [])
        self.assertEqual([(v.value, v.doc) for v in parser.actions['FooAction'].error_type.values()], [
            ('A', []),
            ('B', []),
            ('C', [])
        ])
        self.assertEqual([(v.value, v.doc) for v in parser.actions['FooAction'].error_type.values(include_base_types=False)], [
            ('C', [])
        ])

        self.assertEqual(parser.actions['BarAction'].input_type.base_types, None)
        self.assertEqual(parser.actions['BarAction'].output_type.base_types, None)
        self.assertEqual(parser.actions['BarAction'].error_type.base_types, [parser.types['Foo'], parser.types['Bar']])
        self.assertEqual(list(parser.actions['BarAction'].input_type.members()), [])
        self.assertEqual(list(parser.actions['BarAction'].output_type.members()), [])
        self.assertEqual([(v.value, v.doc) for v in parser.actions['BarAction'].error_type.values()], [
            ('A', []),
            ('B', []),
            ('C', []),
            ('D', [])
        ])
        self.assertEqual([(v.value, v.doc) for v in parser.actions['BarAction'].error_type.values(include_base_types=False)], [
            ('D', [])
        ])

    def test_action_errors_non_enum(self):

        parser = SpecParser()
        try:
            parser.parse_string('''\
action FooAction
    errors (Foo)

struct Foo

struct Bonk

typedef Bonk Bar

enum MyEnum
    A

action BarAction
    errors (MyEnum, Bar)
        A

action BonkAction
    errors (MyEnum)
        A
''')
        except SpecParserError:
            self.assertEqual(parser.errors, [
                ":14: error: Invalid action errors base type 'Bar'",
                ":2: error: Invalid action errors base type 'Foo'",
                ":14: error: Redefinition of enumeration value 'A' from base type",
                ":18: error: Redefinition of enumeration value 'A' from base type"
            ])
        else:
            self.fail()
