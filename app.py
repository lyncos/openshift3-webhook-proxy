from __future__ import print_function

import os
import sys
import json
import requests

from flask import Flask, request
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

generic_url = 'https://%(cluster)s/oapi/v1/namespaces/%(project)s/buildconfigs/%(application)s/webhooks/%(authorization)s/generic'

@app.route('/travis-ci/<cluster>/<project>/<application>', methods=['POST'])
def webhook_travis_ci(cluster, project, application):
    # debug = os.environ.get('DEBUG', '').lower() in ('1', 'true')
    debug = 1

    authorization = request.headers['Authorization']

    fields = json.loads(request.form['payload'])
    print(request.headers)
    print(request.form)
    if debug:
        print('inbound-headers:', request.headers, file=sys.stderr)
        print('inbound-authorization:', authorization, file=sys.stderr)
        print('inbound-payload:', fields, file=sys.stderr)

    if fields['status'] not in (0, None):
        return ''

    url = generic_url % dict(cluster=cluster, project=project,
            application=application, authorization=authorization)

    payload = {}

    payload['type'] = 'git'

    payload['git'] = dict(
        uri=fields['repository']['url'],
        refs='refs/heads/'+fields['branch'],
        commit=fields['commit'],
        author=dict(
            name=fields['author_name'],
            email=fields['author_email']
        ),
        committer=dict(
            name=fields['committer_name'],
            email=fields['committer_email']
        ),
        message=fields['message']
    )

    headers = {}
    headers['Content-Type'] = 'application/json'

    data = json.dumps(payload)

    if os.environ.get('SSL_NO_VERIFY'):
        verify = not(os.environ.get('SSL_NO_VERIFY', '').lower() in ('1', 'true'))
    else:
        verify = request.is_secure

    if debug:
        print('outbound-url:', url, file=sys.stderr)
        print('outbound-payload:', payload, file=sys.stderr)
        print('outbound-verify:', verify, file=sys.stderr)

    try:
        response = requests.post(url, verify=verify, headers=headers, data=data)

    except Exception as e:
        print(e, file=sys.stderr)

        raise

    return ''

@app.route('/')
def hello():
    return 'OpenShift Rocks!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
