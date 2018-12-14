# Copyright 2018 The gRPC Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import os
import json
import time
import datetime

import requests
import jwt

_GITHUB_API_PREFIX = 'https://api.github.com'
_GITHUB_REPO = 'grpc/grpc'
_GITHUB_APP_ID = 22338
_INSTALLATION_ID = 519109
_GITHUB_APP_KEY = open(
    os.environ['HOME'] + '/.ssh/google-grpc-checker.2018-12-13.private-key.pem',
    'r').read()

_ACCESS_TOKEN_CACHE = None


def _jwt_token():
    return jwt.encode(
        {
            'iat': int(time.time()),
            'exp': int(time.time() + 60 * 10),  # expire in 10 minutes
            'iss': _GITHUB_APP_ID,
        },
        _GITHUB_APP_KEY,
        algorithm='RS256')


def _access_token():
    global _ACCESS_TOKEN_CACHE
    if _ACCESS_TOKEN_CACHE == None or _ACCESS_TOKEN_CACHE['exp'] < time.time():
        resp = requests.post(
            url='https://api.github.com/app/installations/%s/access_tokens' %
            _INSTALLATION_ID,
            headers={
                'Authorization': 'Bearer %s' % _jwt_token().decode('ASCII'),
                'Accept': 'application/vnd.github.machine-man-preview+json',
            })
        _ACCESS_TOKEN_CACHE = {
            'token': resp.json()['token'],
            'exp': time.time() + 60
        }
    return _ACCESS_TOKEN_CACHE['token']


def _call(url, method='GET', json=None):
    if not url.startswith('https://'):
        url = _GITHUB_API_PREFIX + url
    headers = {
        'Authorization': 'Bearer %s' % _access_token(),
        'Accept': 'application/vnd.github.antiope-preview+json',
    }
    return requests.request(method=method, url=url, headers=headers, json=json)


def _latest_commit():
    resp = _call('/repos/%s/pulls/%s/commits' % (_GITHUB_REPO,
                                                 os.environ['ghprbPullId']))
    return resp.json()[-1]


def check_on_pr(name, summary, success=True):
    """Create/Update a check on current pull request.

    The check runs are aggregated by their name, so newer check will update the
    older check with the same name.

    Requires environment variable 'ghprbPullId' to indicate which pull request
    should be updated.

    Args:
      name: The name of the check.
      summary: A str in Markdown to be used as the detail information of the check.
      success: A bool indicates whether the check is succeed or not.
    """
    if 'ghprbPullId' not in os.environ:
        print('Missing ghprbPullId env var: not commenting')
        return
    commit = _latest_commit()
    resp = _call(
        '/repos/%s/check-runs' % _GITHUB_REPO,
        method='POST',
        json={
            'name':
            name,
            'head_sha':
            commit['sha'],
            'status':
            'completed',
            'completed_at':
            '%sZ' %
            datetime.datetime.utcnow().replace(microsecond=0).isoformat(),
            'conclusion':
            'success' if success else 'failure',
            'output': {
                'title': name,
                'summary': summary,
            }
        })
    print('Result of Creating/Updating Check on PR:',
          json.dumps(resp.json(), indent=2))
