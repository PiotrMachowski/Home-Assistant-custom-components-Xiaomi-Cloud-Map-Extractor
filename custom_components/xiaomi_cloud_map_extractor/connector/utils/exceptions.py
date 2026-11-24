from abc import ABC
from dataclasses import dataclass, field


class XiaomiCloudMapExtractorException(Exception, ABC):
    pass


@dataclass
class FailedConnectionException(XiaomiCloudMapExtractorException):
    """Xiaomi could not be reached (timeout, DNS, connection reset). Never a reason to log in again."""
    base_exception: Exception

    def __str__(self) -> str:
        return f"Could not connect to Xiaomi Cloud: {type(self.base_exception).__name__} {self.base_exception}".strip()


class DeviceNotFoundException(XiaomiCloudMapExtractorException):
    pass


class InvalidCredentialsException(XiaomiCloudMapExtractorException):
    pass


class FailedLoginException(XiaomiCloudMapExtractorException):
    pass


class SessionExpiredException(FailedLoginException):
    """Xiaomi Cloud rejected the stored serviceToken; the session has to be renewed."""

    def __str__(self) -> str:
        return "Xiaomi Cloud session expired"


class InvalidDeviceTokenException(XiaomiCloudMapExtractorException):
    pass


class FailedMapDownloadException(XiaomiCloudMapExtractorException):
    pass


class FailedMapParseException(XiaomiCloudMapExtractorException):
    pass


@dataclass
class TwoFactorAuthRequiredException(XiaomiCloudMapExtractorException):
    url: str
    headers: dict[str, str] = field(repr=False)
    context: str = field(repr=False)

    def __str__(self) -> str:
        return "Xiaomi requires additional identity verification"


@dataclass
class CaptchaRequiredException(XiaomiCloudMapExtractorException):
    url: str
    image_data: bytes = field(repr=False)

    def __str__(self) -> str:
        return "Xiaomi requires a captcha to log in"
