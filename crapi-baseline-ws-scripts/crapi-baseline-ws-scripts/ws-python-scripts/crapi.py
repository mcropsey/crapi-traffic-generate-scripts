import requests
import tempfile
import os
import config


def _crapi_request(path, method='GET', data=None, token=None, params=None, files=None):
    url = f'{config.CRAPI}{path}'
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if files:
        # let requests set Content-Type with boundary for multipart
        resp = requests.request(method, url, headers=headers, files=files, params=params)
    else:
        headers['Content-Type'] = 'application/json'
        resp = requests.request(method, url, headers=headers, json=data, params=params)
    resp.raise_for_status()
    return resp


def register(user):
    return _crapi_request('/identity/api/auth/signup', 'POST', data={
        'email': user['email'],
        'password': user['password'],
        'name': user['name'],
        'number': user['number'],
    })


def login(user):
    return _crapi_request('/identity/api/auth/login', 'POST', data={
        'email': user['email'],
        'password': user['password'],
    })


def dashboard(user):
    return _crapi_request('/identity/api/v2/user/dashboard', token=user['token'])


def get_vehicles(user):
    return _crapi_request('/identity/api/v2/vehicle/vehicles', token=user['token'])


def add_vehicle(user, vin, pincode):
    return _crapi_request('/identity/api/v2/vehicle/add_vehicle', 'POST',
                          data={'vin': vin, 'pincode': pincode}, token=user['token'])


def get_vehicle_location(user, vehicle_id):
    return _crapi_request(f'/identity/api/v2/vehicle/{vehicle_id}/location', token=user['token'])


def resend_vehicle_email(user):
    return _crapi_request('/identity/api/v2/vehicle/resend_email', 'POST', token=user['token'])


def get_mechanics(user):
    return _crapi_request('/workshop/api/mechanic', token=user['token'])


def make_mechanic_report(user, vin, mechanic_code, problem_details):
    return _crapi_request('/workshop/api/merchant/contact_mechanic', 'POST', data={
        'vin': vin,
        'mechanic_code': mechanic_code,
        'problem_details': problem_details,
        'mechanic_api': f'{config.CRAPI}/workshop/api/mechanic/receive_report',
        'repeat_request_if_failed': False,
        'number_of_repeats': 1,
    }, token=user['token'])


def get_mechanic_report(user, report_id):
    return _crapi_request('/workshop/api/mechanic/mechanic_report', token=user['token'],
                          params={'report_id': report_id})


def get_products(user):
    return _crapi_request('/workshop/api/shop/products', token=user['token'])


def place_order(user, product_id, quantity):
    return _crapi_request('/workshop/api/shop/orders', 'POST',
                          data={'product_id': product_id, 'quantity': quantity},
                          token=user['token'])


def retrieve_order(user, order_id):
    return _crapi_request(f'/workshop/api/shop/orders/{order_id}', token=user['token'])


def update_order(user, order_id, product_id, quantity):
    return _crapi_request(f'/workshop/api/shop/orders/{order_id}', 'PUT',
                          data={'product_id': product_id, 'quantity': quantity},
                          token=user['token'])


def get_past_orders(user):
    return _crapi_request('/workshop/api/shop/orders/all', token=user['token'])


def return_order(user, order_id):
    return _crapi_request('/workshop/api/shop/orders/return_order', 'POST',
                          token=user['token'], params={'order_id': order_id})


def validate_coupon(user, coupon_code):
    return _crapi_request('/community/api/v2/coupon/validate-coupon', 'POST',
                          data={'coupon_code': coupon_code}, token=user['token'])


def apply_coupon(user, coupon_code, amount):
    return _crapi_request('/workshop/api/shop/apply_coupon', 'POST',
                          data={'coupon_code': coupon_code, 'amount': amount},
                          token=user['token'])


def get_recent_posts(user):
    return _crapi_request('/community/api/v2/community/posts/recent', token=user['token'])


def get_post(user, post_id):
    if not user.get('token'):
        return None
    return _crapi_request(f'/community/api/v2/community/posts/{post_id}', token=user['token'])


def add_comment(user, post_id, content):
    return _crapi_request(f'/community/api/v2/community/posts/{post_id}/comment', 'POST',
                          data={'content': content}, token=user['token'])


def make_post(user, title, content):
    return _crapi_request('/community/api/v2/community/posts', 'POST',
                          data={'title': title, 'content': content}, token=user['token'])


def forgot_password(email):
    return _crapi_request('/identity/api/auth/forget-password', 'POST', data={'email': email})


def change_email(user, old_email, new_email):
    return _crapi_request('/identity/api/v2/user/change-email', 'POST',
                          data={'old_email': old_email, 'new_email': new_email},
                          token=user['token'])


def set_avatar(user):
    """Download avatar image and upload it."""
    avatar_url = user.get('avatar', '')
    try:
        img_resp = requests.get(avatar_url, timeout=10)
        img_resp.raise_for_status()
        suffix = '.jpg'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(img_resp.content)
            tmp_path = tmp.name
        with open(tmp_path, 'rb') as f:
            result = _crapi_request('/identity/api/v2/user/pictures', 'POST',
                                    files={'file': (os.path.basename(tmp_path), f, 'image/jpeg')},
                                    token=user['token'])
        os.unlink(tmp_path)
        return result
    except Exception:
        # avatar upload is best-effort
        pass
