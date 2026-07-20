import os
import re

CRAPI = 'http://crapi.cropseyit.com:8888'
MAILHOG = 'http://mail.cropseyit.com:8025'

VIN_REGEX = re.compile(r'\b[A-Z0-9]{17}\b')
PIN_REGEX = re.compile(r'>(\d{4})<\/font>')

USERS_TO_SIMULATE = int(os.environ.get('USERS_TO_SIMULATE', 100))
BATCH_SIZE = 10
