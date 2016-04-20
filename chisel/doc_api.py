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

from .action import Action, ActionError
from .model import Typedef, TypeStruct, TypeEnum, TypeArray, TypeDict
from .spec import SpecParser


DOC_PARSER = SpecParser(spec='''\
union Type
    BuiltinType builtin
    Array array
    Dict dict
    string enum
    string struct
    Typedef typedef

enum BuiltinType
    string
    int
    float
    bool
    date
    datetime
    uuid

struct Array
    Type type
    optional Attr attr

struct Dict
    Type type
    optional Attr attr
    Type key_type
    optional Attr key_attr

struct Enum
    optional string[] doc
    string name
    EnumValue[] values

struct EnumValue
    optional string[] doc
    string value

struct Struct
    optional string[] doc
    string name
    optional bool union
    Member[] members

struct Member
    optional string[] doc
    string name
    optional bool optional
    optional bool nullable
    optional Attr attr
    Type type

struct Attr
    optional float eq
    optional float lt
    optional float lte
    optional float gt
    optional float gte
    optional int len_eq
    optional int len_lt
    optional int len_lte
    optional int len_gt
    optional int len_gte

struct Typedef
    optional string[] doc
    string name
    optional Attr attr
    Type type

struct Action
    string name
    ActionInputOutput input
    optional ActionInputOutput output
    Enum errors

union ActionInputOutput
    Struct struct
    Dict dict

struct RequestUrl
    optional string method
    string url

action doc_index
    output
        string[] names

action doc_request
    input
        string name
    output
        optional string[] doc
        string name
        RequestUrl[] urls
        optional Action action
        optional Struct[] structs
        optional Enum[] enums
        optional Typedef[] typedefs
    errors
        UnknownName
''')


def _referenced_types(struct_types, enum_types, typedef_types, type_, top_level=True):
    if isinstance(type_, TypeStruct) and type_.type_name not in struct_types:
        if not top_level:
            struct_types[type_.type_name] = type_
        for member in type_.members():
            _referenced_types(struct_types, enum_types, typedef_types, member.type, top_level=False)
    elif isinstance(type_, TypeEnum) and type_.type_name not in enum_types:
        if not top_level:
            enum_types[type_.type_name] = type_
    elif isinstance(type_, Typedef) and type_.type_name not in typedef_types:
        if not top_level:
            typedef_types[type_.type_name] = type_
        _referenced_types(struct_types, enum_types, typedef_types, type_.type, top_level=False)
    elif isinstance(type_, TypeArray):
        _referenced_types(struct_types, enum_types, typedef_types, type_.type, top_level=False)
    elif isinstance(type_, TypeDict):
        _referenced_types(struct_types, enum_types, typedef_types, type_.type, top_level=False)
        _referenced_types(struct_types, enum_types, typedef_types, type_.key_type, top_level=False)


class DocIndexApi(Action):
    __slots__ = ()

    def __init__(self, name=None, urls=None):
        Action.__init__(self, self.doc_index, name=name, method='GET', urls=urls, spec=DOC_PARSER)

    @staticmethod
    def doc_index(ctx, dummy_req):
        return {'names': sorted((request.name for request in ctx.app.requests.values()), key=lambda x: x.lower())}


class DocRequestApi(Action):
    __slots__ = ()

    def __init__(self, name=None, urls=None):
        Action.__init__(self, self.doc_request, name=name, method='GET', urls=urls, spec=DOC_PARSER)

    @staticmethod
    def doc_request(ctx, req):
        request = ctx.app.requests.get(req['name'])
        if request is None:
            raise ActionError('UnknownName')

        def url_dict(method, url):
            url_dict = {'url': url}
            if method is not None:
                url_dict['method'] = method
            return url_dict

        response = {
            'name': request.name,
            'urls': [url_dict(method, url) for method, url in request.urls],
        }
        if request.doc:
            response['doc'] = request.doc

        def type_dict(type_):
            if isinstance(type_, TypeArray):
                array_dict = {
                    'type': type_dict(type_.type),
                }
                if type_.attr is not None:
                    array_dict['attr'] = attr_dict(type_.attr)
                return {'array': array_dict}
            elif isinstance(type_, TypeDict):
                return {'dict': dict_dict(type_)}
            elif isinstance(type_, TypeEnum):
                return {'enum': type_.type_name}
            elif isinstance(type_, TypeStruct):
                return {'struct': type_.type_name}
            elif isinstance(type_, Typedef):
                return {'typedef': type_.type_name}
            else:
                return {'builtin': type_.type_name}

        def dict_dict(dict_type):
            dict_dict = {
                'type': type_dict(dict_type.type),
                'key_type': type_dict(dict_type.key_type),
            }
            if dict_type.attr is not None:
                dict_dict['attr'] = attr_dict(dict_type.attr)
            if dict_type.key_attr is not None:
                dict_dict['key_attr'] = attr_dict(dict_type.key_attr)
            return dict_dict

        def attr_dict(attr):
            attr_dict = {}
            if attr.op_eq is not None:
                attr_dict['eq'] = attr.op_eq
            if attr.op_lt is not None:
                attr_dict['lt'] = attr.op_lt
            if attr.op_lte is not None:
                attr_dict['lte'] = attr.op_lte
            if attr.op_gt is not None:
                attr_dict['gt'] = attr.op_gt
            if attr.op_gte is not None:
                attr_dict['gte'] = attr.op_gte
            if attr.op_len_eq is not None:
                attr_dict['len_eq'] = attr.op_len_eq
            if attr.op_len_lt is not None:
                attr_dict['len_lt'] = attr.op_len_lt
            if attr.op_len_lte is not None:
                attr_dict['len_lte'] = attr.op_len_lte
            if attr.op_len_gt is not None:
                attr_dict['len_gt'] = attr.op_len_gt
            if attr.op_len_gte is not None:
                attr_dict['len_gte'] = attr.op_len_gte
            return attr_dict

        if isinstance(request, Action):

            def struct_dict(struct_type):
                struct_dict = {
                    'name': struct_type.type_name,
                    'members': [member_dict(member) for member in struct_type.members()],
                }
                if struct_type.doc:
                    struct_dict['doc'] = struct_type.doc
                if struct_type.union:
                    struct_dict['union'] = True
                return struct_dict

            def member_dict(member):
                member_dict = {
                    'name': member.name,
                    'type': type_dict(member.type),
                }
                if member.doc:
                    member_dict['doc'] = member.doc
                if member.optional:
                    member_dict['optional'] = member.optional
                if member.optional:
                    member_dict['nullable'] = member.nullable
                if member.attr is not None:
                    member_dict['attr'] = attr_dict(member.attr)
                return member_dict

            def enum_dict(enum_type):
                enum_dict = {
                    'name': enum_type.type_name,
                    'values': [enum_value_dict(enum_value) for enum_value in enum_type.values()],
                }
                if enum_type.doc:
                    enum_dict['doc'] = enum_type.doc
                return enum_dict

            def enum_value_dict(enum_value):
                enum_value_dict = {
                    'value': enum_value.value,
                }
                if enum_value.doc:
                    enum_value_dict['doc'] = enum_value.doc
                return enum_value_dict

            def action_input_output(input_output_type):
                if isinstance(input_output_type, TypeDict):
                    return {'dict': dict_dict(input_output_type)}
                return {'struct': struct_dict(input_output_type)}

            struct_types = {}
            enum_types = {}
            typedef_types = {}
            _referenced_types(struct_types, enum_types, typedef_types, request.model.input_type)
            _referenced_types(struct_types, enum_types, typedef_types, request.model.output_type)
            _referenced_types(struct_types, enum_types, typedef_types, request.model.error_type)

            response['action'] = action_dict = {
                'name': request.model.name,
                'input': action_input_output(request.model.input_type),
                'errors': enum_dict(request.model.error_type),
            }
            if not request.wsgi_response:
                action_dict['output'] = action_input_output(request.model.output_type)

            response['structs'] = struct_dicts = []
            for struct_type in sorted(struct_types.values(), key=lambda x: x.type_name.lower()):
                struct_dicts.append(struct_dict(struct_type))

            response['enums'] = enum_dicts = []
            for enum_type in sorted(enum_types.values(), key=lambda x: x.type_name.lower()):
                enum_dicts.append(enum_dict(enum_type))

            response['typedefs'] = typedef_dicts = []
            for typedef_type in sorted(typedef_types.values(), key=lambda x: x.type_name.lower()):
                typedef_dict = {
                    'name': typedef_type.type_name,
                    'type': type_dict(typedef_type.type_name),
                }
                if typedef_type.doc:
                    typedef_dict['doc'] = typedef_type.doc
                if typedef_type.attr is not None:
                    typedef_dict['attr'] = attr_dict(typedef_type.attr)
                typedef_dicts.append(typedef_dict)

        return response
