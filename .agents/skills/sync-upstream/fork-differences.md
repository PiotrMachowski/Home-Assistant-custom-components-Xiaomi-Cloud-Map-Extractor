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
