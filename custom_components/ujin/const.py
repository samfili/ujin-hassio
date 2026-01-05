"""Constants for the Ujin Smart Home integration."""

DOMAIN = "ujin"

# Configuration
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_EMAIL = "email"
CONF_TOKEN = "token"
CONF_AREA_GUID = "area_guid"

# API Configuration
API_BASE_URL = "https://api-product.mysmartflat.ru"
API_GEO_URL = "https://geo.ujin-technologies.com"

# API Endpoints
API_AUTH_EMAIL_SEND = "/api/v1/auth/code/email/send/"
API_AUTH_EMAIL_VERIFY = "/api/v1/auth/code/email/auth/"
API_AUTH_USER = "/api/v1/auth/user/"
API_PROFILE_OBJECTS = "/api/v4/mobile/profile/objects/select/"
API_DEVICES_MAIN = "/api/devices/main/"
API_DEVICES_WSS = "/api/devices/wss/"
API_SEND_SIGNAL = "/api/apartment/send-signal/"
API_APP_INIT = "/api/v1/app/init/"

# API Parameters
API_APP_PARAM = "ujin"
API_PLATFORM_PARAM = "ios"

# Headers
HEADER_APP_TYPE = "X-APP-TYPE"
HEADER_APP_PLATFORM = "X-APP-PLATFORM"
HEADER_APP_LANG = "X-APP-LANG"
HEADER_APP_VERSION = "X-APP-VERSION"
