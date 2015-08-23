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

import chisel

import re
import unittest


# Tests for the action decorator
class TestAction(unittest.TestCase):

    def setUp(self):

        # Application object
        self.app = chisel.Application()
        self.app.specs.parse_string('''\
action myActionDefault
''')

    # Default action decorator
    def test_action_decorator(self):

        @chisel.action
        def myActionDefault(dummy_app, dummy_req):
            return {}
        self.assertTrue(isinstance(myActionDefault, chisel.Action))
        self.assertTrue(isinstance(myActionDefault, chisel.Request))
        self.app.add_request(myActionDefault)
        self.assertEqual(myActionDefault.name, 'myActionDefault')
        self.assertEqual(myActionDefault.urls, ('/myActionDefault',))
        self.assertTrue(isinstance(myActionDefault.model, chisel.spec.ActionModel))
        self.assertEqual(myActionDefault.model.name, 'myActionDefault')
        self.assertEqual(myActionDefault.wsgi_response, False)

    # Default action decorator with missing spec
    def test_action_decorator_unknown_action(self):

        @chisel.action
        def myAction(dummy_app, dummy_req):
            return {}
        self.assertTrue(isinstance(myAction, chisel.Action))
        self.assertTrue(isinstance(myAction, chisel.Request))
        try:
            self.app.add_request(myAction)
        except AssertionError as e:
            self.assertEqual(str(e), "No spec defined for action 'myAction'")
        else:
            self.fail()

    # Action decorator with spec
    def test_action_decorator_spec(self):

        @chisel.action(spec='''\
action myActionName
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.assertTrue(isinstance(myAction, chisel.Action))
        self.assertTrue(isinstance(myAction, chisel.Request))
        self.app.add_request(myAction)
        self.assertEqual(myAction.name, 'myActionName')
        self.assertEqual(myAction.urls, ('/myActionName',))
        self.assertTrue(isinstance(myAction.model, chisel.spec.ActionModel))
        self.assertEqual(myAction.model.name, 'myActionName')
        self.assertEqual(myAction.wsgi_response, False)

    # Action decorator with spec with no actions
    def test_action_decorator_spec_no_actions(self):

        try:
            @chisel.action(spec='')
            def dummy_myAction(dummy_app, dummy_req):
                return {}
        except AssertionError as e:
            self.assertEqual(str(e), 'Action spec must contain exactly one action definition')
        else:
            self.fail()

    # Action decorator with spec with multiple actions
    def test_action_decorator_spec_multiple_actions(self):

        try:
            @chisel.action(spec='''\
action theActionOther
action theAction
''')
            def dummy_myAction(dummy_app, dummy_req):
                return {}
        except AssertionError as e:
            self.assertEqual(str(e), 'Action spec must contain exactly one action definition')
        else:
            self.fail()

    # Action decorator with spec with syntax errors
    def test_action_decorator_spec_syntax_error(self):
        try:
            @chisel.action(spec='''\
asdfasdf
''')
            def dummy_myAction(dummy_app, dummy_req):
                return {}
        except chisel.SpecParserError as e:
            self.assertEqual(str(e), ':1: error: Syntax error')
        else:
            self.fail()

    # Action decorator with name and spec
    def test_action_decorator_named_spec(self):

        @chisel.action(name='theAction', spec='''\
action theActionOther
action theAction
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.assertTrue(isinstance(myAction, chisel.Action))
        self.assertTrue(isinstance(myAction, chisel.Request))
        self.app.add_request(myAction)
        self.assertEqual(myAction.name, 'theAction')
        self.assertEqual(myAction.urls, ('/theAction',))
        self.assertTrue(isinstance(myAction.model, chisel.spec.ActionModel))
        self.assertEqual(myAction.model.name, 'theAction')
        self.assertEqual(myAction.wsgi_response, False)

    # Additional action decorator tests
    def test_action_decorator_other(self):

        # Action decorator with urls, custom response callback, and validate response bool
        @chisel.action(urls=('/foo',), wsgi_response=True)
        def myActionDefault(app, dummy_req):
            return app.response_text('200 OK', 'OK')
        self.app.add_request(myActionDefault)
        self.assertEqual(myActionDefault.name, 'myActionDefault')
        self.assertEqual(myActionDefault.urls, ('/foo',))
        self.assertTrue(isinstance(myActionDefault.model, chisel.spec.ActionModel))
        self.assertEqual(myActionDefault.model.name, 'myActionDefault')
        self.assertEqual(myActionDefault.wsgi_response, True)

    # Test successful action get
    def test_action_success_get(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
    int b
  output
    int c
''')
        def myAction(dummy_app, req):
            return {'c': req['a'] + req['b']}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('GET', '/myAction', query_string='a=7&b=8')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '8'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"c":15}')

    # Test successful action get
    def test_action_success_get_no_validate_output(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
    int b
  output
    int c
''')
        def myAction(dummy_app, req):
            return {'c': req['a'] + req['b']}
        self.app.add_request(myAction)
        self.app.validate_output = False

        status, headers, response = self.app.request('GET', '/myAction', query_string='a=7&b=8')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '8'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"c":15}')

    # Test successful action get with JSONP
    def test_action_success_get_jsonp(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
    int b
  output
    int c
''')
        def myAction(dummy_app, req):
            return {'c': req['a'] + req['b']}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('GET', '/myAction', query_string='a=7&b=8&jsonp=foo')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '14'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), 'foo({"c":15});')

    # Test successful action post
    def test_action_success_post(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
    int b
  output
    int c
''')
        def myAction(dummy_app, req):
            return {'c': req['a'] + req['b']}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{"a": 7, "b": 8}')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '8'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"c":15}')

    # Test successful action get with headers
    def test_action_success_headers(self):

        @chisel.action(spec='''\
action myAction
''')
        def myAction(app, dummy_req):
            app.add_header('MyHeader', 'MyValue')
            return {}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('GET', '/myAction')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '2'),
                                           ('Content-Type', 'application/json'),
                                           ('MyHeader', 'MyValue')])
        self.assertEqual(response.decode('utf-8'), '{}')

    # Test successful action with custom response
    def test_action_success_custom_response(self):

        @chisel.action(wsgi_response=True, spec='''\
action myAction
  input
    string a
  output
    string b
''')
        def myAction(app, req):
            return app.response_text('200 OK', 'Hello ' + str(req['a'].upper()))
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{"a": "world"}')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '11'),
                                           ('Content-Type', 'text/plain')])
        self.assertEqual(response.decode('utf-8'), 'Hello WORLD')

    # Test action error response
    def test_action_error(self):

        @chisel.action(spec='''\
action myAction
  errors
    MyError
''')
        def myAction(dummy_app, dummy_req):
            return {'error': 'MyError'}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '19'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"MyError"}')

    # Test action error response with message
    def test_action_error_message(self):

        @chisel.action(spec='''\
action myAction
  errors
    MyError
''')
        def myAction(dummy_app, dummy_req):
            return {'error': 'MyError', 'message': 'My message'}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '42'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"MyError","message":"My message"}')

    # Test action raised-error response
    def test_action_error_raised(self):

        @chisel.action(spec='''\
action myAction
  errors
    MyError
''')
        def myAction(dummy_app, dummy_req):
            raise chisel.ActionError('MyError')
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '19'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"MyError"}')

    # Test action raised-error response with message
    def test_action_error_message_raised(self):

        @chisel.action(spec='''\
action myAction
  errors
    MyError
''')
        def myAction(dummy_app, dummy_req):
            raise chisel.ActionError('MyError', 'My message')
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '42'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"MyError","message":"My message"}')

    # Test action returning bad error enum value
    def test_action_error_bad_error(self):

        @chisel.action(spec='''\
action myAction
  errors
    MyError
''')
        def myAction(dummy_app, dummy_req):
            return {'error': 'MyBadError'}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '145'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'),
                         '{"error":"InvalidOutput","member":"error","message":"Invalid value \'MyBadError\' (type \'str\') '
                         'for member \'error\', expected type \'myAction_error\'"}')

    # Test action query string decode error
    def test_action_error_invalid_query_string(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('GET', '/myAction', query_string='a')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '63'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"InvalidInput","message":"Invalid key/value pair \'a\'"}')

    # Test action with invalid json content
    def test_action_error_invalid_json(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{a: 7}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertTrue(any(header for header in headers if header[0] == 'Content-Length'))
        self.assertEqual(sorted(header for header in headers if header[0] != 'Content-Length'),
                         [('Content-Type', 'application/json')])
        self.assertTrue(re.search('{"error":"InvalidInput","message":"Invalid request JSON:', response.decode('utf-8')))

    # Test action with invalid HTTP method
    def test_action_error_invalid_method(self):

        @chisel.action(spec='''\
action myAction
  input
    int a
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('FOO', '/myAction', wsgi_input=b'{"a": 7}')
        self.assertEqual(status, '405 Method Not Allowed')
        self.assertEqual(sorted(headers), [('Content-Length', '18'),
                                           ('Content-Type', 'text/plain')])
        self.assertEqual(response.decode('utf-8'), 'Method Not Allowed')

    # Test action with invalid input
    def test_action_error_invalid_input(self):

        @chisel.action(spec='''\
action myAction
  input
    string a
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{"a": 7}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '117'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'),
                         '{"error":"InvalidInput","member":"a","message":"Invalid value 7 (type \'int\') '
                         'for member \'a\', expected type \'string\'"}')

    # Test action with invalid output
    def test_action_error_invalid_output(self):

        @chisel.action(spec='''\
action myAction
  output
    int a
''')
        def myAction(dummy_app, dummy_req):
            return {'a': 'asdf'}
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '120'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'),
                         '{"error":"InvalidOutput","member":"a","message":"Invalid value \'asdf\' (type \'str\') '
                         'for member \'a\', expected type \'int\'"}')

    # Test action with invalid None output
    def test_action_error_none_output(self):

        @chisel.action(spec='''\
action myAction
''')
        def myAction(dummy_app, dummy_req):
            pass
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '200 OK')
        self.assertEqual(sorted(headers), [('Content-Length', '2'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{}')

    # Test action with invalid array output
    def test_action_error_array_output(self):

        @chisel.action(spec='''\
action myAction
''')
        def myAction(dummy_app, dummy_req):
            return []
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '101'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'),
                         '{"error":"InvalidOutput","message":"Invalid value [] (type \'list\'), '
                         'expected type \'myAction_output\'"}')

    # Test action with unexpected error
    def test_action_error_unexpected(self):

        @chisel.action(spec='''\
action myAction
''')
        def myAction(dummy_app, dummy_req):
            raise Exception('My unexpected error')
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '27'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"UnexpectedError"}')

    # Test action HTTP post IO error handling
    def test_action_error_io(self):

        @chisel.action(spec='''\
action myAction
''')
        def myAction(dummy_app, dummy_req):
            return {}
        self.app.add_request(myAction)

        class MyStream(object):
            @staticmethod
            def read():
                raise IOError('FAIL')

        status, headers, response = \
            self.app.request('POST', '/myAction', environ={'wsgi.input': MyStream()},)
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '61'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"IOError","message":"Error reading request content"}')

    # Test action JSON serialization error handling
    def test_action_error_json(self):

        class MyClass(object):
            pass

        @chisel.action(spec='''\
action myAction
  output
    float a
''')
        def myAction(dummy_app, dummy_req):
            return {'a': MyClass()}
        self.app.add_request(myAction)
        self.app.validate_output = False

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '16'),
                                           ('Content-Type', 'text/plain')])
        self.assertEqual(response.decode('utf-8'), 'Unexpected Error')

    # Test action unexpected error response with custom response
    def test_action_error_unexpected_custom_response(self):

        @chisel.action(wsgi_response=True, spec='''\
action myAction
''')
        def myAction(dummy_app, dummy_req):
            raise Exception('FAIL')
        self.app.add_request(myAction)

        status, headers, response = self.app.request('POST', '/myAction', wsgi_input=b'{}')
        self.assertEqual(status, '500 Internal Server Error')
        self.assertEqual(sorted(headers), [('Content-Length', '27'),
                                           ('Content-Type', 'application/json')])
        self.assertEqual(response.decode('utf-8'), '{"error":"UnexpectedError"}')
