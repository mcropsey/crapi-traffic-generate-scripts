import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from faker import Faker

import config
import crapi
import mailhog
from user import create_user

fake = Faker()

# --- Fixed users ---
jane_doe = {
    'name': 'Jane Doe',
    'email': 'jane.doe@fake.com',
    'password': 'N0name!2023',
    'number': '5555555555',
    'userAgent': fake.user_agent(),
    'avatar': fake.image_url(),
    'token': None,
    'new_email': 'jane.doe.new@fake.com',
}

john_smith = {
    'name': 'John Smith',
    'email': 'john.smith@fake.com',
    'password': 'N0name!2023',
    'number': '5555555556',
    'userAgent': fake.user_agent(),
    'avatar': fake.image_url(),
    'token': None,
    'new_email': 'john.smith.new@fake.com',
}

user1 = {
    'name': 'John Smith',
    'email': 'crapi_user1@nonamesec.com',
    'password': 'N0name!2023',
    'number': '5555555557',
    'userAgent': fake.user_agent(),
    'avatar': fake.image_url(),
    'token': None,
    'new_email': 'crapi_user1_new@nonamesec.com',
}

user2 = {
    'name': 'Jane Doe',
    'email': 'crapi_user2@nonamesec.com',
    'password': 'N0name!2023',
    'number': '5555555558',
    'userAgent': fake.user_agent(),
    'avatar': fake.image_url(),
    'token': None,
    'new_email': 'crapi_user2_new@nonamesec.com',
}


def baseline_user(user=None, order_quantity=1):
    try:
        if user is None:
            user = create_user()

        # register user
        crapi.register(user)

        # login user
        login_resp = crapi.login(user)
        user['token'] = login_resp.json().get('token')
        if not user['token']:
            return

        # simulate same API behavior that web UI generates
        crapi.dashboard(user)
        crapi.get_vehicles(user)

        # baseline mailhog UI functionality
        mailhog.get_emails(50)

        # search for registration email to get VIN and PIN
        search_result = mailhog.search_emails(user['email'])
        items = search_result.json().get('items', [])
        if not items:
            print(f'No registration email found for {user["email"]}')
            return

        email_id = items[0]['ID']
        email_resp = mailhog.get_email(email_id)
        email_body = email_resp.json()['Content']['Body']

        # parse VIN
        vin_match = config.VIN_REGEX.search(email_body)
        if not vin_match:
            print(f'VIN not found in email for {user["email"]}')
            return
        vin = vin_match.group(0)

        # parse PIN
        pin_match = config.PIN_REGEX.search(email_body)
        if not pin_match:
            print(f'PIN not found in email for {user["email"]}')
            return
        pin = pin_match.group(1)

        # add vehicle
        crapi.resend_vehicle_email(user)
        crapi.add_vehicle(user, vin, pin)

        # simulate web UI behavior
        crapi.dashboard(user)
        vehicles_resp = crapi.get_vehicles(user)
        vehicles = vehicles_resp.json()
        vehicle_id = vehicles[0]['uuid']

        # 'click' refresh location
        crapi.get_vehicle_location(user, vehicle_id)

        # set avatar
        crapi.set_avatar(user)

        # video upload skipped - no video file

        # 'click' contact mechanic
        crapi.get_mechanics(user)
        mechanic_report_resp = crapi.make_mechanic_report(
            user, vin, 'TRAC_JHN', fake.sentence()
        )
        report_id = mechanic_report_resp.json()['response_from_mechanic_api']['id']
        crapi.get_mechanic_report(user, report_id)

        # 'click' Shop
        products_resp = crapi.get_products(user)
        products = products_resp.json().get('products', [])

        # validate and apply coupon
        crapi.validate_coupon(user, 'TRAC075')
        crapi.apply_coupon(user, 'TRAC075', 75)

        # place order and simulate web UI behavior
        product_id = products[0]['id']
        order_resp = crapi.place_order(user, product_id, order_quantity)
        order_id = order_resp.json()['id']
        crapi.retrieve_order(user, order_id)
        crapi.update_order(user, order_id, product_id, 2)
        past_orders_resp = crapi.get_past_orders(user)
        past_orders = past_orders_resp.json().get('orders', [])

        # return order
        past_order_id = past_orders[0]['id']
        crapi.return_order(user, past_order_id)

        # 'click' community
        recent_posts_resp = crapi.get_recent_posts(user)
        recent_posts = recent_posts_resp.json()

        # 'read' all posts
        for post in recent_posts:
            try:
                crapi.add_comment(user, post['id'], fake.paragraph())
                crapi.get_post(user, post['id'])
            except Exception:
                pass  # just keep going

        # make a forum post
        my_post_resp = crapi.make_post(user, fake.sentence(), '\n'.join(fake.paragraphs(2)))
        my_post_id = my_post_resp.json()['id']
        crapi.get_post(user, my_post_id)

        # change email and forgot password
        crapi.forgot_password(user['email'])
        crapi.change_email(user, user['email'], user.get('new_email', user['email']))

    except Exception as err:
        if user:
            print(f'Error running baseline for {user.get("email")} / {user.get("name")}')
        print(err)


def run_pool(users_list, order_quantity=1):
    with ThreadPoolExecutor(max_workers=config.BATCH_SIZE) as executor:
        futures = {executor.submit(baseline_user, u, order_quantity): u for u in users_list}
        for future in as_completed(futures):
            future.result()  # surface any unhandled exceptions


if __name__ == '__main__':
    print('Baseline started')

    users = [None] * config.USERS_TO_SIMULATE
    run_pool(users)

    print('Baseline complete')

    if os.environ.get('FIRST_RUN'):
        for fixed_user in [jane_doe, john_smith, user1, user2]:
            baseline_user(fixed_user, order_quantity=-999999999)
