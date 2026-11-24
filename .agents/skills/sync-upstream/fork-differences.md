# Fork differences: sync preservation checklist

[`FORK.md`](../../../FORK.md) is authoritative. This file is the sync view: every active difference,
the files that implement it, and the proof that must still pass after an upstream import. An import
that merges cleanly but breaks a row here is a failed sync.

| Area (FORK.md anchor) | Protected implementation | Proof after the sync |
|---|---|---|
| [Project identity](../../../FORK.md#project-identity) | `manifest.json` (`name`, `documentation`, `issue_tracker`, `codeowners`), `hacs.json` `name`, `README.md`, `.github/ISSUE_TEMPLATE/`, `translations/en.json` reauth text | The domain, folder, zip name and `hacs.json` `filename` are unchanged; links point at the fork |
| [Test suite](../../../FORK.md#test-suite) | `tests/`, `requirements_test.txt`, `pyproject.toml` | `pytest` passes; no test was deleted or loosened |
| [CI and lint](../../../FORK.md#ci) | `.github/workflows/tests.yml`, `hacs.yaml`, `hassfest.yaml`; `pyproject.toml` ruff rules | `ruff check .`; no `automerge.yaml`, `lint_python.yml` or `dev` triggers come back |
| [Release packaging](../../../FORK.md#release-packaging) | `.github/workflows/release.yaml`, `hacs.json` | The workflow tests the commit and uploads `xiaomi_cloud_map_extractor.zip` with `manifest.json` at its root |
| [Device list timeout](../../../FORK.md#home-device-list-timeout) | `connector/xiaomi_cloud/connector.py` `_get_devices_from_home` | `tests/test_cloud_connector.py` |
| [Cloud session renewal](../../../FORK.md#cloud-session-renewal) | `connector/xiaomi_cloud/connector.py` (`renew_session`, `pass_token` in `XiaomiCloudConnectorConfig`), `connector/__init__.py` (`_ensure_session`, `_recover_session`), `__init__.py` `session_saver` | `tests/test_cloud_session.py`, `tests/test_session_lifecycle.py` |
| [Network errors never log in](../../../FORK.md#network-errors-no-login) | `connector/xiaomi_cloud/connector.py` (`NETWORK_ERRORS`, `strict` device lookup), `connector/__init__.py` | `tests/test_session_lifecycle.py::test_network_timeout_never_triggers_a_login`, `tests/test_cloud_session.py` |
| [Re-authentication explains why](../../../FORK.md#reauth-reason) | `coordinator.py` (`AuthIssue`), `config_flow.py` (`reauth_captcha`, `reauth_verification`, `auth_saved_credentials`, `auth_two_factor`), `translations/en.json`, `connector/utils/exceptions.py` | `tests/test_reauth_session.py` |
