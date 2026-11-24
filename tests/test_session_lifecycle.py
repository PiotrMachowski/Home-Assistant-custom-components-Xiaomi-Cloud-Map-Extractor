"""XiaomiCloudMapExtractorConnector: how the cloud session is kept alive between map updates."""

from __future__ import annotations

import asyncio
import datetime
from unittest.mock import MagicMock, patch

import pytest
from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes

from custom_components.xiaomi_cloud_map_extractor.connector import XiaomiCloudMapExtractorConnector
from custom_components.xiaomi_cloud_map_extractor.connector.model import (
    XiaomiCloudMapExtractorConnectorConfiguration,
    XiaomiCloudMapExtractorConnectorStatus,
)
from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import (
    CaptchaRequiredException,
    FailedConnectionException,
)
from custom_components.xiaomi_cloud_map_extractor.connector.vacuums.base.model import VacuumApi
from custom_components.xiaomi_cloud_map_extractor.connector.vacuums.vacuum_viomi import ViomiCloudVacuum
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import (
    XiaomiCloudConnectorConfig,
)

from .fake_xiaomi import API, PASS_TOKEN, SERVICE_LOGIN, SSECURITY, USER_ID, FakeResponse, FakeXiaomiCloud

DEVICE_ID = "428789378"
MAP_URL = "https://maps.example.com/map/0"


def map_configuration() -> XiaomiCloudMapExtractorConnectorConfiguration:
    return XiaomiCloudMapExtractorConnectorConfiguration(
        host="192.168.1.14",
        token="0" * 32,
        username="user@example.com",
        password="secret",
        server="de",
        used_api=VacuumApi.VIOMI,
        device_id=DEVICE_ID,
        mac="60:1d:9d:3b:87:37",
        model="viomi.vacuum.v8",
        image_config=ImageConfig(),
        colors=ColorsPalette(),
        drawables=[],
        sizes=Sizes(),
        texts=[],
    )


def stored_session(*, expires_in: datetime.timedelta, pass_token: str | None = PASS_TOKEN):
    return XiaomiCloudConnectorConfig(
        username="user@example.com",
        password="secret",
        server="de",
        user_id=USER_ID,
        c_user_id="cUser-abc",
        service_token="stored-service-token",
        expiration=datetime.datetime.now() + expires_in,
        ssecurity=SSECURITY,
        device_id="abcdef",
        pass_token=pass_token,
    )


def vacuum_cloud() -> FakeXiaomiCloud:
    """A cloud that knows one Viomi vacuum and serves its map."""
    cloud = FakeXiaomiCloud()
    cloud.encrypted_api("/v2/homeroom/gethome", {"result": {"homelist": [{"id": "1", "uid": int(USER_ID)}]}})
    cloud.encrypted_api(
        "/v2/home/home_device_list",
        {
            "result": {
                "device_info": [
                    {
                        "did": DEVICE_ID,
                        "name": "Viomi V8",
                        "model": "viomi.vacuum.v8",
                        "token": "0" * 32,
                        "spec_type": "urn:miot-spec-v2:device:vacuum:0000A006:viomi-v8:1",
                        "localip": "192.168.1.14",
                        "mac": "60:1D:9D:3B:87:37",
                    }
                ]
            }
        },
    )
    cloud.encrypted_api("/v2/home/get_interim_file_url", {"result": {"url": MAP_URL}})
    cloud.on("GET", MAP_URL, lambda r: FakeResponse(body=b"raw-map-bytes"))
    return cloud


@pytest.fixture(autouse=True)
def no_map_parsing():
    """Map parsing is not under test; the session handling around the download is."""
    with (
        patch.object(ViomiCloudVacuum, "decode_and_parse", return_value=MagicMock()),
        patch("custom_components.xiaomi_cloud_map_extractor.connector.to_image", return_value=b"png"),
    ):
        yield


class SessionSaver:
    def __init__(self) -> None:
        self.saved: list[XiaomiCloudConnectorConfig] = []

    async def __call__(self, config: XiaomiCloudConnectorConfig) -> None:
        self.saved.append(config)


def make_connector(cloud: FakeXiaomiCloud, session: XiaomiCloudConnectorConfig | None, saver: SessionSaver):
    return XiaomiCloudMapExtractorConnector(cloud.session_creator, map_configuration(), session, saver)


async def test_expiring_session_is_renewed_with_pass_token_not_password() -> None:
    cloud = vacuum_cloud()
    cloud.valid_service_tokens.add("stored-service-token")
    cloud.pass_token_login()
    cloud.password_login("captcha")  # what a password login would get on a server
    cloud.sts_issuing("renewed-service-token")
    saver = SessionSaver()
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(hours=6)), saver)

    data = await connector.get_data()

    assert data.status == XiaomiCloudMapExtractorConnectorStatus.OK
    assert cloud.password_login_count() == 0
    assert cloud.calls(SERVICE_LOGIN)[0].cookies["passToken"] == PASS_TOKEN
    assert saver.saved and saver.saved[-1].service_token == "renewed-service-token"


async def test_token_rejected_by_api_is_renewed_and_map_download_retried() -> None:
    cloud = vacuum_cloud()  # "stored-service-token" is NOT valid any more -> API answers 401
    cloud.pass_token_login()
    cloud.password_login("captcha")
    cloud.sts_issuing("renewed-service-token")
    saver = SessionSaver()
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(days=20)), saver)

    data = await connector.get_data()

    assert data.status == XiaomiCloudMapExtractorConnectorStatus.OK
    assert data.map_data_raw == b"raw-map-bytes"
    assert cloud.password_login_count() == 0
    assert saver.saved[-1].service_token == "renewed-service-token"


async def test_network_timeout_never_triggers_a_login() -> None:
    cloud = vacuum_cloud()
    cloud.valid_service_tokens.add("stored-service-token")
    cloud.pass_token_login()
    cloud.password_login("captcha")

    def timeout(_request):
        raise asyncio.TimeoutError()

    cloud.on("POST", f"{API}/v2/homeroom/gethome", timeout)
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(days=20)), SessionSaver())

    with pytest.raises(FailedConnectionException):
        await connector.get_data()

    assert cloud.calls(SERVICE_LOGIN) == []
    assert cloud.password_login_count() == 0


async def test_rejected_pass_token_falls_back_to_password_login_and_surfaces_captcha() -> None:
    cloud = vacuum_cloud()
    cloud.pass_token_login(accepted=False)
    cloud.password_login("captcha")
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(days=20)), SessionSaver())

    with pytest.raises(CaptchaRequiredException):
        await connector.get_data()

    assert cloud.password_login_count() == 1


async def test_expiring_session_keeps_working_when_renewal_times_out() -> None:
    cloud = vacuum_cloud()
    cloud.valid_service_tokens.add("stored-service-token")
    cloud.password_login("captcha")

    def timeout(_request):
        raise asyncio.TimeoutError()

    cloud.on("GET", SERVICE_LOGIN, timeout)
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(hours=6)), SessionSaver())

    data = await connector.get_data()

    assert data.status == XiaomiCloudMapExtractorConnectorStatus.OK
    assert cloud.password_login_count() == 0


async def test_failed_proactive_renewal_is_not_retried_on_every_update() -> None:
    cloud = vacuum_cloud()
    cloud.valid_service_tokens.add("stored-service-token")
    cloud.pass_token_login(accepted=False)
    cloud.password_login("captcha")
    connector = make_connector(cloud, stored_session(expires_in=datetime.timedelta(hours=6)), SessionSaver())

    await connector.get_data()
    connector.force_refresh()
    await connector.get_data()

    assert len(cloud.calls(SERVICE_LOGIN)) == 1
    assert cloud.password_login_count() == 0


async def test_first_password_login_is_persisted_so_restarts_reuse_it() -> None:
    """Entries imported from YAML start without a stored session."""
    cloud = vacuum_cloud()
    cloud.pass_token_login(accepted=False)
    cloud.password_login("ok")
    cloud.sts_issuing("token-from-password")
    saver = SessionSaver()
    connector = make_connector(cloud, None, saver)

    data = await connector.get_data()

    assert data.status == XiaomiCloudMapExtractorConnectorStatus.OK
    assert saver.saved[-1].service_token == "token-from-password"
    assert saver.saved[-1].pass_token == PASS_TOKEN
