from __future__ import print_function
import os
import sys
import json
import requests
from flatten_dict.reducer import make_reducer
from flatten_dict import flatten
from flask import Flask, request
from werkzeug.contrib.fixers import ProxyFix

bitbucketServerBaseUri = 'ssh://git@jira-scm-videotron.com:7999/'

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

#generic_url = 'https://%(cluster)s/oapi/v1/namespaces/%(project)s/buildconfigs/%(application)s/webhooks/%(authorization)s/generic'
generic_url = 'https://%(cluster)s/%(project)s/buildconfigs/%(application)s/webhooks/%(authorization)s/generic'



def capitalize_keys(d):
    result = {}
    for key, value in d.items():
        upper_key = 'BITBUCKET_' + key.upper()
        result[upper_key] = value
    return result

def makePayloadFromPrOpen(data):
    payload = {}
    payload['type'] = 'git'

    payload['git'] = dict(
        uri = bitbucketServerBaseUri + data['pullRequest']['fromRef']['repository']['project']['key'].lower() + '/' + data['pullRequest']['fromRef']['repository']['name'] + '.git',
        refs='refs/heads/'+data['pullRequest']['fromRef']['displayId'],
        commit=data['pullRequest']['fromRef']['latestCommit'],
        author=dict(
            name=data['pullRequest']['author']['user']['displayName'],
            email=data['pullRequest']['author']['user']['emailAddress']
        ),
        committer=dict(
            name=data['actor']['displayName'],
            email=data['actor']['emailAddress']
        ),
        message=data['pullRequest']['title']
    )
    
    payload['env'] = flatten(data, reducer=make_reducer(delimiter='_'))
    payload['env'] = capitalize_keys(payload['env'])
    
    return payload

@app.route('/bitbucket/<cluster>/<project>/<application>', methods=['POST'])
def webhook_travis_ci(cluster, project, application):
    # debug = os.environ.get('DEBUG', '').lower() in ('1', 'true')
    debug = True

    authorization = request.headers['Authorization']
    bitbucketEventKey = request.headers['X-Event-Key']
  
    fields = json.loads(request.data)
 
    if debug:
        print('inbound-headers:', request.headers, file=sys.stderr)
        print('inbound-authorization:', authorization, file=sys.stderr)
        print('inbound-payload:', fields, file=sys.stderr)

    if 'pullrequest:created' in bitbucketEventKey:
        if fields['pullRequest'] not in (0, None):
            payload = makePayloadFromPrOpen(fields)

    url = generic_url % dict(cluster=cluster, project=project,
            application=application, authorization=authorization)

    payload = makePayloadFromPrOpen(fields)


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
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
