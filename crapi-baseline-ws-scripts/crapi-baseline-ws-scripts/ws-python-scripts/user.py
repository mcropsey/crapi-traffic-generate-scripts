import random
import string
from faker import Faker

fake = Faker()

_in_use_emails = set()
_in_use_phones = set()


def _generate_unique_email(first_name, last_name):
    while True:
        email = fake.email()
        if email not in _in_use_emails:
            _in_use_emails.add(email)
            return email


def _generate_unique_phone():
    while True:
        phone = ''.join(random.choices(string.digits, k=10))
        if phone not in _in_use_phones:
            _in_use_phones.add(phone)
            return phone


def _generate_password(length=15):
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation
    while True:
        pwd = ''.join(random.choices(chars, k=length))
        # ensure complexity
        if (any(c.islower() for c in pwd) and
                any(c.isupper() for c in pwd) and
                any(c.isdigit() for c in pwd) and
                any(c in string.punctuation for c in pwd)):
            return pwd


def create_user():
    first_name = fake.first_name()
    last_name = fake.last_name()
    return {
        'name': f'{first_name} {last_name}',
        'email': _generate_unique_email(first_name, last_name),
        'new_email': _generate_unique_email(first_name, last_name),
        'password': _generate_password(),
        'number': _generate_unique_phone(),
        'userAgent': fake.user_agent(),
        'avatar': fake.image_url(),
        'token': None,
    }
