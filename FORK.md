# Fork scope and upstream differences

This repository is Igloczek's hard fork of
[PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor),
published as **Better Xiaomi Cloud Map Extractor**. Upstream's v3 line (`dev_extracted_libraries`,
released as v3.0.0-alpha-1 to alpha-24) is the baseline; this file records where the fork behaves
differently and how to import upstream changes. Planned work is in [ROADMAP.md](ROADMAP.md),
released changes in [CHANGELOG.md](CHANGELOG.md).

## Branches

- `master` is the fork's only development branch. It started at upstream `dev_extracted_libraries`
  `688fe3e` (v3.0.0-alpha-24).
- `v2` keeps upstream's legacy v2 line (upstream `master` at `62285a7`, v2.2.5 plus three
  commits). It is frozen: no fixes or releases. Its three commits after the common base are covered
  on `master`: the user-agent changes (`410ba42`, `62285a7`) are already in v3's
  `connector/xiaomi_cloud/utils.py`, and `43b20eb` only edited upstream's donation links.

## Compatibility

The integration domain `xiaomi_cloud_map_extractor`, the folder
`custom_components/xiaomi_cloud_map_extractor`, the release asset `xiaomi_cloud_map_extractor.zip`,
the config entry data and options keys, entity unique ids and the storage file names keep their
upstream names and meaning. The fork is a drop-in replacement for the v3 alphas: existing config
entries, entity ids and dashboards keep working without setting the vacuum up again. Changing any of
these needs the maintainer's explicit decision and a migration.

## Upstream snapshot

- Upstream baseline: `688fe3e` (`upstream/dev_extracted_libraries`, tag `v3.0.0-alpha-24`), reviewed
  on 2026-11-24. Upstream's last push was 2026-02-20.
- Upstream `master` (v2) is not a source of imports; see **Branches**.
- Upstream open pull requests are imported one by one with `git cherry-pick -x` or as a reviewed
  re-implementation; the triage that ranks them is in [ROADMAP.md](ROADMAP.md).
- Refresh this snapshot in the same change as an upstream import. Recompute the ahead/behind counts
  with `git log --left-right --cherry-pick --oneline upstream/dev_extracted_libraries...master`.

## Active differences

Each row is a preservation criterion for an upstream import. The
[sync checklist](.agents/skills/sync-upstream/fork-differences.md) maps every row to the files that
implement it and the proof that must still pass.

| Area | Behaviour in this fork | Why |
| --- | --- | --- |
| <a id="project-identity"></a>Project identity | The manifest and HACS name are **Better Xiaomi Cloud Map Extractor**; `documentation`, `issue_tracker` and `codeowners` point at the fork; the README, issue forms and re-authentication text carry the fork's name. The domain and the other names under **Compatibility** stay upstream's. | The fork needs its own identity and tracker without breaking installed setups. |
| <a id="test-suite"></a>Test suite | `tests/` runs on `pytest-homeassistant-custom-component` with the Xiaomi cloud and the vacuum mocked: the config flow (credentials, captcha, two-factor, several vacuums, duplicates, errors), setup and unload, and which connector errors start re-authentication. `requirements_test.txt` pins the test harness and lists the integration's requirements. | Upstream has no tests. |
| <a id="ci"></a>CI and lint | `tests.yml` runs `ruff check .` (correctness rules, `pyproject.toml`) and `pytest` on Python 3.14 for pushes to and pull requests against `master`. HACS validation runs every check, including `issues` (the repository has HACS topics). `manifest.json` does not list `Pillow`, which Home Assistant provides and hassfest forbids in custom integrations. There is no `dev` branch and no master→dev automerge job, and upstream's `lint_python` job (whose steps mostly ended in `|| true`) is replaced. | Upstream CI could not fail on a real problem, and the fork lands every change on `master`. |
| <a id="release-packaging"></a>Release packaging | `release.yaml` runs lint and tests on the released commit, sets the manifest `version` to the tag without its `v`, and attaches `xiaomi_cloud_map_extractor.zip` with the integration files at the archive root, as `hacs.json` (`zip_release`) expects. | A release must not ship a commit that fails the suite, and HACS installs from that zip. |
| <a id="home-device-list-timeout"></a>Device list timeout | A home whose device list times out or fails to connect is skipped (`_get_devices_from_home` catches the tuple `(FailedConnectionException, TimeoutError)`). | Upstream wrote `except A \| B`, which raises `TypeError` when an exception arrives, so one slow home aborted setup with "Unknown error". |
| <a id="cloud-session-renewal"></a>Cloud session renewal | The `passToken` Xiaomi sets on every login (credentials, QR, two-factor) is stored with the session (`pass_token` in the connector store; older stores load without it). A session close to its stored expiration, or one the API rejects (401/403 or an `auth err` body), is renewed through `serviceLogin` with that `passToken` and the map download is retried; a password login runs only when Xiaomi refuses the `passToken`. A session that can't be renewed right now keeps being used until Xiaomi rejects it, and a refused proactive renewal is retried at most hourly. Every renewal or background login is written back to the store. | Upstream logged in with the password one day before the 30-day expiry and after every restart past it, and Xiaomi answers server-side password logins with a captcha or identity check, so the map stopped every month (upstream #697, PR #777). |
| <a id="network-errors-no-login"></a>Network errors never log in | Timeouts and connection errors during login, renewal, device lookup and API calls raise `FailedConnectionException` (update retried), never a login error; device lookup for the configured server no longer turns an error into "device not found". | A timeout used to be reported as bad credentials or a missing device, which started reauth or a password login. |
| <a id="reauth-reason"></a>Re-authentication explains why | The coordinator keeps why reauth started (`AuthIssue`); the reauth flow opens with a captcha or account-verification step (with Xiaomi's verification link) when that was the cause, offers logging in again with the saved credentials, and the two-factor step shows the verification link and retries the login when submitted empty. `ConfigEntryAuthFailed` carries a translated message; captcha images, request headers and session tokens never reach the log. | The cause and the verification link were only in the log, next to a dump of the captcha image bytes. |

## Upstream sync preservation contract

Every row in **Active differences** is a preservation criterion for an upstream import, including
changes that merge without conflicts. Before importing, follow
[.agents/skills/sync-upstream/SKILL.md](.agents/skills/sync-upstream/SKILL.md).

- Reconcile upstream improvements at the affected boundary; do not freeze an old implementation.
- Never resolve a conflict by choosing one side wholesale. Keep the fork behaviour and reapply the
  upstream change around it.
- Never delete a fork test, a FORK.md row, a documentation anchor or the sync skill to make an import
  pass.
- If upstream now provides the same behaviour, prove equivalence with the tests, then move the row
  to **Superseded differences** and record the upstream commit.

## Superseded differences

None yet.

## Scope boundaries

- Keep the fork focused on concrete bugs and features with a Home Assistant use case.
- A vendor-specific fix needs a fixture (a captured, scrubbed map or cloud response) or a report from
  someone with the device; see the pre-release rule in [AGENTS.md](AGENTS.md).
- Prefer small modules for fork-only logic so upstream imports touch fewer lines.
- When a new intentional difference is added, record it here with what it changes and why, and add it
  to the sync checklist.

## Importing from upstream

This checkout has an `upstream` remote. In a fresh clone:

```sh
git remote add upstream https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor.git
```

Follow [the sync skill](.agents/skills/sync-upstream/SKILL.md) for the procedure.
