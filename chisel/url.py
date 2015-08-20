#
# Copyright (C) 2012-2015 Craig Hobbs
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

from .compat import basestring_, urllib_parse_quote, urllib_parse_unquote, xrange_
from .model import JsonDate, JsonDatetime, JsonUUID

from datetime import date, datetime
from uuid import UUID


# Encode an object as a URL query string
def _encode_query_string_flatten(obj, parent, encoding):
    if isinstance(obj, dict):
        if obj:
            for member in obj:
                for child in _encode_query_string_flatten(obj[member], parent + (urllib_parse_quote(member, encoding=encoding),), encoding):
                    yield child
        elif parent:
            yield (parent, '')
    elif isinstance(obj, list) or isinstance(obj, tuple):
        if obj:
            for i in xrange_(len(obj)):
                for child in _encode_query_string_flatten(obj[i], parent + (urllib_parse_quote(str(i), encoding=encoding),), encoding):
                    yield child
        elif parent:
            yield (parent, '')
    else:
        if isinstance(obj, date):
            ostr = str(JsonDate(obj)).strip('"')
        elif isinstance(obj, datetime):
            ostr = str(JsonDatetime(obj)).strip('"')
        elif isinstance(obj, UUID):
            ostr = str(JsonUUID(obj)).strip('"')
        elif isinstance(obj, bool):
            ostr = 'true' if obj else 'false'
        else:
            ostr = obj if isinstance(obj, basestring_) else str(obj)
        yield (parent, urllib_parse_quote(ostr, encoding=encoding))

def encode_query_string(obj, encoding='utf-8'):
    return '&'.join('='.join(('.'.join(k), v)) for k, v in
                    sorted(_encode_query_string_flatten(obj, (), encoding)))


# Decode an object from a URL query string
def decode_query_string(query_string, encoding='utf-8'):

    # Build the object
    result = [None]
    for key_value_str in query_string.split('&'):

        # Ignore empty key/value strings
        if not key_value_str:
            continue

        # Split the key/value string
        key_value = key_value_str.split('=')
        if len(key_value) != 2:
            raise ValueError("Invalid key/value pair '" + key_value_str + "'")
        value = urllib_parse_unquote(key_value[1], encoding=encoding)

        # Find/create the object on which to set the value
        parent = result
        key_parent = 0
        for key in (urllib_parse_unquote(key, encoding=encoding) for key in key_value[0].split('.')):
            obj = parent[key_parent]

            # Array key?  First "key" of an array must start with "0".
            if isinstance(obj, list) or (obj is None and key == '0'):

                # Create this key's container, if necessary
                if obj is None:
                    obj = parent[key_parent] = []

                # Create the index for this key
                try:
                    key = int(key)
                except:
                    raise ValueError("Invalid key/value pair '" + key_value_str + "'")
                if key == len(obj):
                    obj.append(None)
                elif key < 0 or key > len(obj):
                    raise ValueError("Invalid key/value pair '" + key_value_str + "'")

            # Dictionary key
            else:

                # Create this key's container, if necessary
                if obj is None:
                    obj = parent[key_parent] = {}

                # Create the index for this key
                if obj.get(key) is None:
                    obj[key] = None

            # Update the parent object and key
            parent = obj
            key_parent = key

        # Set the value
        if parent[key_parent] is not None:
            raise ValueError("Duplicate key '" + key_value_str + "'")
        parent[key_parent] = value

    return result[0] if (result[0] is not None) else {}
