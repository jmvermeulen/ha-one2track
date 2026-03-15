"""Constants for the One2Track integration."""

import logging

DOMAIN = "one2track"
LOGGER = logging.getLogger(__package__)

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCOUNT_ID = "account_id"

DEFAULT_SCAN_INTERVAL = 60  # seconds

BASE_URL = "https://www.one2trackgps.com"
LOGIN_URL = f"{BASE_URL}/auth/users/sign_in"

# Watch command codes
CMD_REFRESH_LOCATION = "0039"
CMD_SHUTDOWN = "0048"
CMD_SET_ALARM = "0057"
CMD_GPS_TRACKING = "0078"
CMD_STEP_COUNTER = "0079"
