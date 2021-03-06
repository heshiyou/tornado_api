# -*- coding: utf-8 -*-

# Copyright 2012 Didip Kerabat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import urllib
import functools

from tornado import httpclient, escape

class Stripe(object):
    api_hostname = 'api.stripe.com'
    api_version = 'v1'

    resources = set([
        'charges',
        'customers',
        'invoices',
        'invoiceitems',
        'tokens',
        'events',
        'plans',
        'coupons',
        'subscription',
        'incoming'
    ])

    def __init__(self, api_key, blocking=False):
        self.api_key  = api_key
        self.blocking = blocking
        self.url      = None

        if blocking:
            self.httpclient_instance = httpclient.HTTPClient()
        else:
            self.httpclient_instance = httpclient.AsyncHTTPClient()


    def __getattr__(self, name):
        '''
        Builds API URL.
        Example:
            tornado_api.Stripe('api_key').plans.get(callback=lambda x: x)
        '''
        if name in self.__class__.resources:
            self.url = '/'.join([self.url or self.api_endpoint, name])
            return self
        else:
            raise AttributeError(name)


    @property
    def api_endpoint(self):
        return 'https://%s:@%s/%s' % (self.api_key, self.__class__.api_hostname, self.__class__.api_version)


    def id(self, id):
        '''
        Append ID to constructed URL.
        Example:
            customer_id = 'cus_xyz'
            tornado_api.Stripe('api_key').customers.id(customer_id).subscription.post(callback=lambda x: x)
        '''
        self.url = '/'.join([self.url or self.api_endpoint, str(id)])
        return self


    def reset_url(self):
        self.url = None


    def get(self, **kwargs):
        return self._call_check_blocking_first('GET', **kwargs)


    def post(self, **kwargs):
        return self._call_check_blocking_first('POST', **kwargs)


    def put(self, **kwargs):
        return self._call_check_blocking_first('PUT', **kwargs)


    def delete(self, **kwargs):
        return self._call_check_blocking_first('DELETE', **kwargs)


    def _call_check_blocking_first(self, http_method, **kwargs):
        if self.blocking:
            http_response = self._call(http_method, **kwargs)
            return self._parse_response(None, http_response)
        else:
            return self._call(http_method, **kwargs)


    def _call(self, http_method, callback=None, **kwargs):
        copy_of_url = self.url

        # reset self.url
        self.reset_url()

        httpclient_args = [copy_of_url]

        if not self.blocking:
            if not callback:
                callback = lambda x: x

            httpclient_args.append(functools.partial(self._parse_response, callback))

        httpclient_kwargs = { 'method': http_method }

        if http_method != 'GET' and kwargs:
            httpclient_kwargs['body'] = urllib.urlencode(self._nested_dict_to_url(kwargs))

        return self.httpclient_instance.fetch(*httpclient_args, **httpclient_kwargs)


    def _nested_dict_to_url(self, d):
        """
        We want post vars of form:
        {'foo': 'bar', 'nested': {'a': 'b', 'c': 'd'}}
        to become (pre url-encoding):
        foo=bar&nested[a]=b&nested[c]=d
        """
        stk = []
        for key, value in d.items():
            if isinstance(value, dict):
                n = {}
                for k, v in value.items():
                    n["%s[%s]" % (key, k)] = v
                stk.extend(self._nested_dict_to_url(n))
            else:
                stk.append((key, value))
        return stk


    def _parse_response(self, callback, response):
        """Parse a response from the API"""
        try:
            res = escape.json_decode(response.body)
        except Exception, e:
            e.args += ('API response was: %s' % response,)
            raise e

        if res.get('error'):
            raise Exception('Error(%s): %s' % (res['error']['type'], res['error']['message']))

        if callback:
            callback(res)
        else:
            return res

