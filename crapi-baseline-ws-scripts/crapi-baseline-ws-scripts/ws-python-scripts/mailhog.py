import requests
import config


def _mailhog_request(path, method='GET', data=None, params=None):
    url = f'{config.MAILHOG}/api{path}'
    headers = {'Content-Type': 'application/json'}
    resp = requests.request(method, url, json=data, params=params, headers=headers)
    resp.raise_for_status()
    return resp


def get_emails(limit=50):
    return _mailhog_request('/v2/messages', params={'limit': limit})


def search_emails(address):
    return _mailhog_request('/v2/search', params={'kind': 'containing', 'query': address})


def get_email(email_id):
    return _mailhog_request(f'/v1/messages/{email_id}')
