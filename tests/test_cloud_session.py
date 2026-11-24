"""XiaomiCloudConnector: passToken renewal, error classification and safe exceptions."""

from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import asdict

import pytest

from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import (
    CaptchaRequiredException,
    FailedConnectionException,
    SessionExpiredException,
    TwoFactorAuthRequiredException,
)
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import (
    XiaomiCloudConnector,
    XiaomiCloudConnectorConfig,
)

from .fake_xiaomi import (
    API,
    NEW_SSECURITY,
    PASS_TOKEN,
    SERVICE_LOGIN,
    SSECURITY,
    USER_ID,
    FakeResponse,
    FakeXiaomiCloud,
)


def stored_config(**overrides) -> XiaomiCloudConnectorConfig:
    values = dict(
        username="user@example.com",
        password="secret",
        server="de",
        user_id=USER_ID,
        c_user_id="cUser-abc",
        service_token="old-service-token",
        expiration=datetime.datetime.now() + datetime.timedelta(hours=6),
        ssecurity=SSECURITY,
        device_id="abcdef",
        pass_token=PASS_TOKEN,
    )
    values.update(overrides)
    return XiaomiCloudConnectorConfig(**values)


async def test_password_login_stores_pass_token_in_config() -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login()
    cloud.password_login("ok")
    cloud.sts_issuing("token-from-password")
    connector = XiaomiCloudConnector(cloud.session_creator, server="de")

    await connector.login_with_credentials("user@example.com", "secret")

    config = connector.to_config()
    assert config.pass_token == PASS_TOKEN
    assert config.service_token == "token-from-password"


async def test_config_stored_before_pass_token_existed_still_loads() -> None:
    legacy = asdict(stored_config())
    legacy.pop("pass_token")
    legacy["expiration"] = legacy["expiration"].isoformat()

    config = XiaomiCloudConnectorConfig.from_dict(legacy)

    assert config.pass_token is None


async def test_renew_session_uses_pass_token_without_password() -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login()
    cloud.password_login("ok")
    cloud.sts_issuing("renewed-service-token")
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    assert await connector.renew_session() is True

    login_call = cloud.calls(SERVICE_LOGIN)[-1]
    assert login_call.cookies["passToken"] == PASS_TOKEN
    assert login_call.cookies["userId"] == USER_ID
    assert cloud.password_login_count() == 0
    config = connector.to_config()
    assert config.service_token == "renewed-service-token"
    assert config.ssecurity == NEW_SSECURITY
    assert config.expiration > datetime.datetime.now() + datetime.timedelta(days=29)
    assert config.pass_token == PASS_TOKEN


async def test_renew_session_returns_false_when_pass_token_rejected() -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login(accepted=False)
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    assert await connector.renew_session() is False
    assert connector.to_config().service_token == "old-service-token"


async def test_renew_session_without_pass_token_does_not_call_xiaomi() -> None:
    cloud = FakeXiaomiCloud()
    connector = await XiaomiCloudConnector.from_config(stored_config(pass_token=None), cloud.session_creator)

    assert await connector.renew_session() is False
    assert cloud.requests == []


async def test_renew_session_network_error_is_a_connection_failure() -> None:
    cloud = FakeXiaomiCloud()

    def timeout(_request):
        raise asyncio.TimeoutError()

    cloud.on("GET", SERVICE_LOGIN, timeout)
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    with pytest.raises(FailedConnectionException):
        await connector.renew_session()


async def test_login_timeout_is_a_connection_failure_not_bad_credentials() -> None:
    cloud = FakeXiaomiCloud()

    def timeout(_request):
        raise asyncio.TimeoutError()

    cloud.on("GET", SERVICE_LOGIN, timeout)
    connector = XiaomiCloudConnector(cloud.session_creator, server="de")

    with pytest.raises(FailedConnectionException):
        await connector.login_with_credentials("user@example.com", "secret")


async def test_api_401_raises_session_expired() -> None:
    cloud = FakeXiaomiCloud()
    cloud.encrypted_api("/v2/home/get_interim_file_url", {"result": {"url": "x"}})
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    with pytest.raises(SessionExpiredException):
        await connector.execute_api_call_encrypted(f"{API}/v2/home/get_interim_file_url", {"data": "{}"})


async def test_api_timeout_raises_connection_failure() -> None:
    cloud = FakeXiaomiCloud()

    def timeout(_request):
        raise asyncio.TimeoutError()

    cloud.on("POST", f"{API}/v2/home/get_interim_file_url", timeout)
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    with pytest.raises(FailedConnectionException):
        await connector.execute_api_call_encrypted(f"{API}/v2/home/get_interim_file_url", {"data": "{}"})


async def test_api_plain_auth_error_body_raises_session_expired() -> None:
    """Xiaomi sometimes answers 200 with an unencrypted auth error instead of 401."""
    cloud = FakeXiaomiCloud()
    cloud.on(
        "POST",
        f"{API}/v2/home/get_interim_file_url",
        lambda r: FakeResponse(body='{"code":3,"message":"auth err"}'),
    )
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    with pytest.raises(SessionExpiredException):
        await connector.execute_api_call_encrypted(f"{API}/v2/home/get_interim_file_url", {"data": "{}"})


async def test_captcha_exception_never_renders_image_bytes() -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login(accepted=False)
    cloud.password_login("captcha")
    connector = XiaomiCloudConnector(cloud.session_creator, server="de")

    with pytest.raises(CaptchaRequiredException) as info:
        await connector.login_with_credentials("user@example.com", "secret")

    assert info.value.image_data.startswith(b"\xff\xd8")
    for rendered in (str(info.value), repr(info.value)):
        assert "\\x" not in rendered
        assert "JFIF" not in rendered
    assert "captcha" in str(info.value).lower()


async def test_two_factor_exception_message_carries_the_link_but_no_headers(caplog) -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login(accepted=False)
    cloud.password_login("two_factor")
    connector = XiaomiCloudConnector(cloud.session_creator, server="de")

    with caplog.at_level(logging.DEBUG), pytest.raises(TwoFactorAuthRequiredException) as info:
        await connector.login_with_credentials("user@example.com", "secret")

    assert "identity/authStart" in info.value.url
    assert "User-Agent" not in str(info.value)
    assert "User-Agent" not in repr(info.value)


async def test_debug_log_does_not_contain_session_secrets(caplog) -> None:
    cloud = FakeXiaomiCloud()
    cloud.pass_token_login()
    cloud.password_login("ok")
    cloud.sts_issuing("renewed-service-token")
    connector = await XiaomiCloudConnector.from_config(stored_config(), cloud.session_creator)

    with caplog.at_level(logging.DEBUG):
        connector.is_authenticated()
        await connector.renew_session()

    assert "renewed-service-token" not in caplog.text
    assert "old-service-token" not in caplog.text
    assert PASS_TOKEN not in caplog.text
    assert NEW_SSECURITY not in caplog.text
