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

import hashlib
from itertools import chain
import posixpath

from pkg_resources import resource_string

from .app_defs import ENVIRON_CTX
from .request import Request


class StaticRequest(Request):
    __slots__ = ('package', 'resource_name', 'headers', 'content', 'etag')

    EXT_TO_CONTENT_TYPE = {
        '.css': 'text/css',
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.png': 'image/png',
        '.txt': 'text/plain',
    }

    def __init__(self, package, resource_name, content_type=None, headers=None, name=None, urls=None, doc=None):
        if name is None:
            name = resource_name
        if urls is None:
            urls = '/' + posixpath.join(*resource_name.split(posixpath.sep)[1:])
        if doc is None:
            doc = ('The "{0}" package\'s static resource, "{1}".'.format(package, resource_name),)

        Request.__init__(self, name=name, method='GET', urls=urls, doc=doc)

        self.package = package
        self.resource_name = resource_name
        if content_type is None:
            content_type = self.EXT_TO_CONTENT_TYPE.get(posixpath.splitext(resource_name)[1].lower())
            assert content_type, 'Unknown content type for "{0}" package\'s "{1}" resource'.format(package, resource_name)
        self.headers = tuple(chain(headers or (), [('Content-Type', content_type)]))
        self._load_content()

    def _load_content(self):
        self.content = resource_string(self.package, self.resource_name)
        md5 = hashlib.md5()
        md5.update(self.content)
        self.etag = md5.hexdigest()

    def __call__(self, environ, start_response):
        ctx = environ[ENVIRON_CTX]

        # If we're developing re-load the content
        if ctx.app.validate_output:
            self._load_content()

        # Check the etag - is the resource modified?
        etag = environ.get('HTTP_IF_NONE_MATCH')
        if etag == self.etag:
            start_response('304 Not Modified', [])
            return []

        start_response('200 OK', list(chain(self.headers, [('ETag', self.etag)])))
        return [self.content]
