"""Constants for the Mystiebel integration."""

DOMAIN = "mystiebel"
WS_URL = "wss://serviceapi.mystiebel.com/ws/v1"

# API Configuration
BASE_URL = "https://auth.mystiebel.com"
SERVICE_URL = "https://serviceapi.mystiebel.com"

# App Configuration
APP_NAME = "MyStiebelApp"
APP_VERSION_ANDROID = "Android_2.3.0"
USER_AGENT = f"{APP_NAME}/2.3.0 Dalvik/2.1.0"

# Timing Constants
WEBSOCKET_HEARTBEAT = 30  # seconds
WEBSOCKET_RECONNECT_INITIAL = 5  # seconds
WEBSOCKET_RECONNECT_MAX = 300  # 5 minutes
TOKEN_REFRESH_MARGIN = 300  # Refresh token 5 minutes before expiry
API_RATE_LIMIT_DELAY = 1  # Minimum seconds between API calls

# Message ID Range
MSG_ID_MIN = 1_000_000
MSG_ID_MAX = 9_999_999
MSG_ID_LONG_MIN = 1_000_000_000
MSG_ID_LONG_MAX = 9_999_999_999

# List of essential read-only sensors.
# These will be enabled by default. All other sensor-type entities will be disabled by default.
ESSENTIAL_SENSORS = [
    15,  # Dome Temperature
    2378,  # Current Target Temperature
    2395,  # Mixed Water Volume
    2758,  # Operating Mode
    2388,  # SG-Ready State
    1111,  # Compressor (state)
    1116,  # Heating Element (state)
    1130,  # Defrosting (state)
]

# List of essential control entities (switches, numbers, selects).
# These will also be enabled by default. All other controls will be disabled.
ESSENTIAL_CONTROLS = [
    13,  # Setpoint Temperature Comfort
    14,  # Setpoint Temperature Eco
    2466,  # Eco heating mode
    2382,  # Boost Request (Select)
    2487,  # Hot Water Plus Requested (Switch)
    2498,  # Weekly Hygiene Program Requested (Switch)
    2384,  # Frost Protection Requested (Switch)
    2481,  # End of Vacation (Switch)
]