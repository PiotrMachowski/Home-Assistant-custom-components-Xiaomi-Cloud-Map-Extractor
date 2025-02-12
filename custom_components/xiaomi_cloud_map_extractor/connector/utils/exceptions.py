from abc import ABC
from dataclasses import dataclass


class XiaomiCloudMapExtractorException(Exception, ABC):
    pass


@dataclass
class FailedConnectionException(XiaomiCloudMapExtractorException):
    base_exception: Exception


class DeviceNotFoundException(XiaomiCloudMapExtractorException):
    pass


class InvalidCredentialsException(XiaomiCloudMapExtractorException):
    pass


class FailedLoginException(XiaomiCloudMapExtractorException):
    pass


class InvalidDeviceTokenException(XiaomiCloudMapExtractorException):
    pass


class FailedMapDownloadException(XiaomiCloudMapExtractorException):
    pass


class FailedMapParseException(XiaomiCloudMapExtractorException):
    pass


@dataclass
class TwoFactorAuthRequiredException(XiaomiCloudMapExtractorException):
    url: str
