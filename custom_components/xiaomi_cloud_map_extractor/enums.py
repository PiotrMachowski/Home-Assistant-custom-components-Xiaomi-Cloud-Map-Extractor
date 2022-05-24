from enum import Enum


class CameraStatus(Enum):
    EMPTY_MAP = 'Empty map'
    FAILED_LOGIN = 'Failed to login'
    FAILED_TO_RETRIEVE_DEVICE = 'Failed to retrieve device'
    FAILED_TO_RETRIEVE_MAP_FROM_VACUUM = 'Failed to retrieve map from vacuum'
    INITIALIZING = 'Initializing'
    NOT_LOGGED_IN = 'Not logged in'
    OK = 'OK'
    LOGGED_IN = 'Logged in'
    TWO_FACTOR_AUTH_REQUIRED = 'Two factor auth required (see logs)'
    UNABLE_TO_PARSE_MAP = 'Unable to parse map'
    UNABLE_TO_RETRIEVE_MAP = 'Unable to retrieve map'

    def __str__(self):
        return str(self._value_)
