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

from .app import Application
from .compat import func_name, iteritems, itervalues
from .model import VALIDATE_QUERY_STRING, VALIDATE_JSON_INPUT, VALIDATE_JSON_OUTPUT, ValidationError, TypeStruct, TypeString
from .request import Request
from .spec import SpecParser
from .url import decode_query_string

import cgi
import json


def action(_action_callback=None, **kwargs):
    """
    Chisel action request decorator
    """
    return Action(_action_callback, **kwargs) if _action_callback is not None else lambda fn: Action(fn, **kwargs)


class ActionError(Exception):
    """
    Action error response exception
    """

    __slots__ = ('error', 'message')

    def __init__(self, error, message=None):
        Exception.__init__(self, error)
        self.error = error
        self.message = message


class _ActionErrorInternal(Exception):
    __slots__ = ('error', 'message', 'member')

    def __init__(self, error, message=None, member=None):
        Exception.__init__(self, error)
        self.error = error
        self.message = message
        self.member = member


class Action(Request):
    """
    Chisel action request
    """

    __slots__ = ('action_callback', 'model', 'wsgi_response')

    JSONP = 'jsonp'

    def __init__(self, action_callback, name=None, urls=None, spec=None, wsgi_response=False):

        # Spec provided?
        model = None
        if spec is not None:
            parser = SpecParser()
            parser.parse_string(spec)
            if name is not None:
                model = parser.actions[name]
            else:
                assert len(parser.actions) == 1, 'Action spec must contain exactly one action definition'
                model = next(itervalues(parser.actions))

        # Use the action model name, if available
        if name is None:
            name = model.name if model is not None else func_name(action_callback)

        Request.__init__(self, self._wsgi_callback, name=name, urls=urls)
        self.action_callback = action_callback
        self.model = model
        self.wsgi_response = wsgi_response

    def onload(self, app):
        Request.onload(self, app)

        # Get the action model, if necessary
        if self.model is None:
            self.model = app.specs.actions.get(self.name)
            assert self.model is not None, "No spec defined for action '%s'" % (self.name,)

    def _wsgi_callback(self, environ, dummy_start_response):
        ctx = environ[Application.ENVIRON_CTX]

        # Check the method
        is_get = (environ['REQUEST_METHOD'] == 'GET')
        if not is_get and environ['REQUEST_METHOD'] != 'POST':
            return ctx.response_text('405 Method Not Allowed', 'Method Not Allowed')

        # Handle the action
        try:
            # Get the input dict
            if is_get:

                # Decode the query string
                validate_mode = VALIDATE_QUERY_STRING
                try:
                    request = decode_query_string(environ.get('QUERY_STRING', ''))
                except Exception as exc:
                    ctx.log.warning("Error decoding query string for action '%s': %s", self.name, environ.get('QUERY_STRING', ''))
                    raise _ActionErrorInternal('InvalidInput', str(exc))

            else:

                # Read the request content
                try:
                    content = environ['wsgi.input'].read()
                except:
                    ctx.log.warning("I/O error reading input for action '%s'", self.name)
                    raise _ActionErrorInternal('IOError', 'Error reading request content')

                # De-serialize the JSON request
                validate_mode = VALIDATE_JSON_INPUT
                try:
                    content_type = environ.get('CONTENT_TYPE')
                    content_charset = ('utf-8' if content_type is None else
                                       cgi.parse_header(content_type)[1].get('charset', 'utf-8'))
                    request = json.loads(content.decode(content_charset))
                except Exception as exc:
                    ctx.log.warning("Error decoding JSON content for action '%s': %s", self.name, content)
                    raise _ActionErrorInternal('InvalidInput', 'Invalid request JSON: ' + str(exc))

            # JSONP?
            if is_get and self.JSONP in request:
                ctx.jsonp = str(request[self.JSONP])
                del request[self.JSONP]

            # Add url arguments
            if ctx.url_args is not None:
                validate_mode = VALIDATE_QUERY_STRING
                for url_arg, url_value in iteritems(ctx.url_args):
                    if url_arg in request or url_arg == self.JSONP:
                        ctx.log.warning("Duplicate URL argument member '%s' for action '%s'", url_arg, self.name)
                        raise _ActionErrorInternal('InvalidInput', "Duplicate URL argument member '%s'" % (url_arg,))
                    request[url_arg] = url_value

            # Validate the request
            try:
                request = self.model.input_type.validate(request, validate_mode)
            except ValidationError as exc:
                ctx.log.warning("Invalid input for action '%s': %s", self.name, str(exc))
                raise _ActionErrorInternal('InvalidInput', str(exc), exc.member)

            # Call the action callback
            try:
                response = self.action_callback(ctx, request)
                if self.wsgi_response:
                    return response
                elif response is None:
                    response = {}
            except ActionError as exc:
                response = {'error': exc.error}
                if exc.message is not None:
                    response['message'] = exc.message
            except Exception as exc:
                ctx.log.exception("Unexpected error in action '%s'", self.name)
                raise _ActionErrorInternal('UnexpectedError')

            # Validate the response
            if ctx.app.validate_output:
                if hasattr(response, '__contains__') and 'error' in response:
                    response_type = TypeStruct()
                    response_type.add_member('error', self.model.error_type)
                    response_type.add_member('message', TypeString(), optional=True)
                else:
                    response_type = self.model.output_type

                try:
                    response_type.validate(response, mode=VALIDATE_JSON_OUTPUT)
                except ValidationError as exc:
                    ctx.log.error("Invalid output returned from action '%s': %s", self.name, str(exc))
                    raise _ActionErrorInternal('InvalidOutput', str(exc), exc.member)

        except _ActionErrorInternal as exc:
            response = {'error': exc.error}
            if exc.message is not None:
                response['message'] = exc.message
            if exc.member is not None:
                response['member'] = exc.member

        # Serialize the response as JSON
        return ctx.response_json(response, is_error='error' in response)
