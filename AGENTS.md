# Agent guide

## Fork relationship

- This repository is Igloczek's hard fork of `PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor`, published as **Better Xiaomi Cloud Map Extractor**. Upstream is abandoned; its v3 line (`dev_extracted_libraries`, v3.0.0-alpha-24) is the baseline, and the legacy v2 line is frozen on the `v2` branch.
- [`FORK.md`](FORK.md) holds the compatibility promise, the differences from upstream and the import rules. Read it before changing fork-specific behaviour or importing upstream code. Every row under **Active differences** is a preservation criterion.
- Add every intentional fork-only feature or fix to `FORK.md` with what it changes and why, and add it to the [sync checklist](.agents/skills/sync-upstream/fork-differences.md).
- [`ROADMAP.md`](ROADMAP.md) holds planned work, the upstream triage and postponed items; [`CHANGELOG.md`](CHANGELOG.md) holds released changes. Do not keep a record of completed work in a standing document.
- To import an upstream commit or open upstream pull request, follow [`.agents/skills/sync-upstream/SKILL.md`](.agents/skills/sync-upstream/SKILL.md). Never push to `upstream` and never comment on upstream issues or pull requests.

## Compatibility

The domain stays `xiaomi_cloud_map_extractor` so the fork is a drop-in replacement: config entries, entity ids, options and dashboards of v3-alpha users keep working. Do not rename the domain, the folder, the release zip, config entry keys, entity unique ids or storage keys. A change that needs a new key adds a config entry migration (`VERSION`/`MINOR_VERSION` and `async_migrate_entry`) with a test that loads an entry written by v3.0.0-alpha-24.

## Project map

- Home Assistant custom integration in `custom_components/xiaomi_cloud_map_extractor/`.
- Setup and config: `__init__.py` (entry → `XiaomiCloudMapExtractorConnectorConfiguration`), `config_flow.py` (cloud login by credentials or QR, captcha, two-factor, vacuum selection, reauth, YAML import), `options_flow.py`, `legacy.py` (v2 YAML schema and import).
- Runtime: `coordinator.py` maps connector exceptions to `ConfigEntryAuthFailed` (reauth) or `UpdateFailed` (retry); entities in `image.py`, `camera.py`, `sensor.py`, `binary_sensor.py`, `button.py`, `switch.py`.
- Cloud access: `connector/xiaomi_cloud/connector.py` (login, sessions, device discovery, encrypted API calls); the session is persisted per MAC by `store.py`.
- Vendors: `connector/vacuums/vacuum_*.py` download the map; parsing and drawing live in the external `vacuum-map-parser-*` packages pinned in `manifest.json`.
- `scripts/map_processor.py` is a standalone offline map renderer.

## Local checks

```sh
uv venv -p 3.14 .venv && uv pip install -p .venv -r requirements_test.txt   # once
.venv/bin/ruff check .
.venv/bin/pytest
```

- Tests use `pytest-homeassistant-custom-component`; the Xiaomi cloud and the vacuum are always mocked (`tests/conftest.py`). Never put a real account, token, IP or map in a fixture; scrub captured data first.
- Keep `requirements_test.txt` in step with `manifest.json` requirements; bump the pinned harness to follow Home Assistant releases.
- Run the smallest check that proves a change (one test file or `-k`), then the full `pytest` before pushing. It takes a few seconds.
- CI (`.github/workflows/tests.yml`, `hacs.yaml`, `hassfest.yaml`) runs on every push and pull request to `master`.

## Every bug improves the test suite

A bug that reached a user is also a bug in the test suite: the suite let it through. Fix both, so the suite grows with every bug and the same class of problem cannot come back.

- **Red first.** Before fixing, write a test that reproduces the bug and fails on the current code. Run it against the unfixed code and see it fail, then fix and see it pass. A test that was never red proves nothing.
- **Find the gap, not only the case.** Ask why the suite missed it and close that gap for the whole class: a mock that answers more politely than the real Xiaomi cloud, a flow step never driven to the end, a config entry shape only older versions write, a vendor map never fed through the parser. Extend the fixtures and helpers so every later test gets the coverage too.
- **Test where the bug lives.** Flow and setup behaviour through Home Assistant (`hass.config_entries.flow`, `async_setup`); cloud protocol handling at the connector with recorded, scrubbed responses; map parsing with a captured map file. A bug that crossed levels gets a test at each.
- **Keep fixtures real.** When a user's report shows a response, model, or map the fixtures lack, add a scrubbed copy under `tests/fixtures/` so it stays covered.
- **Report what testing turns up.** Fix extra problems when they are in scope; otherwise name them to the maintainer instead of fixing them silently or leaving them unmentioned.
- **Never weaken the suite to pass.** Do not delete, loosen or skip a test to make a change pass. A flaky test is a bug of its own.
- In the hand-off or report, name the test that was red before the fix and the gap in the suite it closes.

## Who decides what ships

Agents drive this project: they investigate, reproduce, build, test, open pull requests and prepare releases without waiting to be asked. Whether a change may be merged and released depends on what kind of change it is. Sort every change into one of these classes before merging; when it is not clearly class 1, it is class 2.

1. **Clear bug: merge it yourself.** The report is binary (it works or it does not), the reproduction is a red test, and the fix restores documented or obviously intended behaviour with nothing visible changing beyond the fix. Merge after the local checks pass on the exact head.
2. **Needs the maintainer's call: build it fully, then stop.** Anything that is not an obvious bug, and every change to what users see or how they set things up: config and options flow steps, wording and translations, entity names, defaults and which entities are enabled, how the map is drawn, new options or behaviour, compatibility or migrations, dependency upgrades of the map parsers. Do all the work, open the pull request, do not merge or release it, and hand it over.
3. **Cannot be reproduced here: pre-release.** The change depends on a vacuum, region or account state we do not have. Follow the pre-release rule under "GitHub releases".

**What a hand-off contains.** It goes in the chat with the maintainer, never on GitHub: no hand-offs, screenshots or summaries as pull request or issue comments, and short pull request descriptions. GitHub comments are only for external contributors (the pre-release flow). Present it with the chat's visualization tools: the problem and the change in a short paragraph written for a user; what it looks like (config flow screens, the rendered map) before and after; how to try it; the alternatives and your recommendation; what is proven and what is not. End with one question the maintainer can answer yes or no, or by picking an option.

**Releases are batched.** Merging does not mean releasing. Before a release, check other running agent threads, open pull requests close to merging, and what `master` gained since the last tag (`git log <last tag>..origin/master`). Release on its own only for urgent breakage: setup that fails for everyone, lost configuration, or leaked credentials.

## GitHub releases

- `.github/workflows/release.yaml` tests the tagged commit, sets the manifest `version` and attaches `xiaomi_cloud_map_extractor.zip` when a GitHub release is published. Check it when changing packaging, and check `hacs.json` (`zip_release`, `filename`) with it.
- Releases use the fork's own `vX.Y.Z` tags in sequence from the last release (`gh release list --limit 1`); upstream's `v3.0.0-alpha-N` tags are history. The first fork version is the maintainer's call. Check the tag is free (`git ls-remote --tags origin vX.Y.Z`) before `gh release create`.
- Every release adds its `CHANGELOG.md` section in the same push, crediting imported upstream pull requests and their authors.
- A change we cannot verify ourselves goes out as a pre-release first: keep the pull request open, push a `vX.Y.Z-beta.N` tag on its head, publish it with `--prerelease` so the stable release stays latest, and check the uploaded zip carries the change. Ask the reporter on the fork's issue to have their AI agent install it (HACS → Redownload → pick the beta version), test it and report back, with a short prompt that only links that comment, plus the manual install and revert steps and exactly what to report. Merge and release the stable version after they confirm.
- Run `gh` in the authorized local environment.

## Privacy

Debug logs, diagnostics and issue attachments of this integration can contain Xiaomi account tokens, `ssecurity`, `serviceToken`, `passToken`, device tokens, IPs and map images. Never paste them into commits, tests or GitHub; scrub them first. Code that logs or exports session data must redact it.
