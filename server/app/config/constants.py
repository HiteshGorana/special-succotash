from os import getenv
from os.path import dirname, join

MONGO_HOST = getenv("MONGO_HOST")
MONGO_PORT = getenv("MONGO_PORT")
REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = getenv("REDIS_PORT")
MONGO_DATABASE = getenv("MONGO_DATABASE")
WEBSOCKET_HOST = getenv("WEBSOCKET_HOST", "api.localhost")
IMPORT_CSV_TO_MONGODB = getenv("IMPORT_CSV_TO_MONGODB", "").lower() == "true"
DEBUG = getenv("DEBUG", "").lower() == "true"
STORE_STATUS_HISTORY = "store_status_history"
STORE_HOURS_DATA = "store_hours_data"
STORE_TIMEZONE_DATA = "store_timezone_data"
DEFAULT_TIMEZONE = "America/Chicago"
DEFAULT_START_HOURS_SHOP = "00:00:00"
DEFAULT_END_HOURS_SHOP = "23:59:59"
NUMBER_OF_DAYS_TO_BE_REMOVED_FROM_TODAY = 56
NDIGITS = 2
WEEK = 7  # in days
DAY = 1  # in days
HOUR = 1  # in hours
ACTIVE = "active"
INACTIVE = "inactive"
BATCH_SIZE = 2 if DEBUG else 5000
STORE_MONITOR_DATA = {
    STORE_STATUS_HISTORY: join(dirname(__file__), "../data/store_status_history.csv"),
    STORE_HOURS_DATA: join(dirname(__file__), "../data/store_hours_data.csv"),
    STORE_TIMEZONE_DATA: join(dirname(__file__), "../data/store_timezone_data.csv"),
}
