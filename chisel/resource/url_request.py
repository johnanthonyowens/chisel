#
# Copyright (C) 2012 Craig Hobbs
#
# See README.md for license.
#

from ..app import ResourceType

import urllib2


# Url request resource type
class UrlRequestResourceType(ResourceType):

    def __init__(self):

        ResourceType.__init__(self, "url_request", UrlRequestResource, None)


# Url request resource
class UrlRequestResource:

    def __init__(self, hostUrl):

        self.hostUrl = hostUrl
        self.reset()

    def reset(self):

        # Reset the request parameters
        self.data = []
        self.header = []
        self.unredirected_header = []

    def send(self, url):

        # Build the request object, send the request, and read the response
        request = urllib2.Request(self.hostUrl.rstrip("/") + "/" + url.lstrip("/"))
        for data in self.data:
            request.add_data(data)
        for header in self.header:
            request.add_header(*header)
        for unredirected_header in self.unredirected_header:
            request.add_unredirected_header(*unredirected_header)
        response = urllib2.urlopen(request)
        responseString = response.read()

        # Reset the resource
        self.reset()

        return responseString

    def add_data(self, data):

        self.data.append(data)

    def add_header(self, key, val):

        self.header.append((key, val))

    def add_unredirected_header(self, key, val):

        self.unredirected_header.append((key, val))
