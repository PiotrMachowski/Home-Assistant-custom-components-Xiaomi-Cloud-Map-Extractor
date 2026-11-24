# Roadmap

What this fork plans to work on next. The current state is described in the [README](README.md);
released changes are in [CHANGELOG.md](CHANGELOG.md); the differences from upstream are in
[FORK.md](FORK.md).

## How to propose work

Open an issue on the [fork tracker](https://github.com/Igloczek/Home-Assistant-custom-components-Better-Xiaomi-Cloud-Map-Extractor/issues)
with the vacuum model, the integration and Home Assistant versions, a debug log with tokens removed,
and what you expected. A change is planned when it can be proven: by a test with a scrubbed fixture
of the cloud response or map, or by someone with the vacuum testing a pre-release. Every change comes
with a test that fails first (see [AGENTS.md](AGENTS.md)).

## In progress

- **Re-authentication crash.** Reauth reaches `confirm_data` without an existing entry and ends in
  "Unknown error occurred". Includes upstream #730 and the regression test from upstream PR #754.
- **Cloud login robustness.** Session renewal with the `passToken` (upstream PR #777, #697) and
  a reauth flow that explains captcha and account verification (#780: the link) are in review.
  Still open: PR #793 (cloud region selection), #700, #712 and the `verifyEmail` finish location
  in #780.

## Next, in order

The upstream backlog on 2026-11-24 was 141 open issues and 27 open pull requests. Clusters are ranked
by how many users they hit (issues + comments + 👍 on upstream), restricted to what still happens on
v3.0.0-alpha-24. Issue and PR numbers refer to the upstream repository.

1. **QR login on Home Assistant 2026.9+.** The QR flow fails on current Home Assistant and its
   placeholders show as `MISSING_VALUE`; the login link opens a sign-in page instead of approving.
   Import upstream PRs #796 and #795, and #766 with a timeout and without swallowing every
   exception. Closes #779, helps #730. Touches `config_flow.py` like the two threads above, so it
   starts after they merge.
2. **Secrets in logs and diagnostics.** The debug log prints `ssecurity`/`psecurity`
   (`connector.py`, extension-pragma branch) and other session data, and users paste debug logs into
   public issues; diagnostics export the map decryption key in `device_data`. Redact session
   secrets in every log line and in diagnostics, with a test that scans log output. Closes #778.
3. **Ijai maps (the largest v3 cluster).** `Padding is incorrect`, `FailedMapDownloadException`,
   `Failed to get wifi_sn`, `expected str, NoneType` on ijai v1/v2/v3/v17/v18, S10, S12, X20 Max.
   Import #725 first (parser author: isK3, hex key type), then one combined change from #782 (URL
   fallback, wifi_sn length), #792 (alternate key ids; or #785/#787 for the device_id "0" case), #789
   (shared devices, S12 live map) and #786. Needs scrubbed map fixtures from reporters; ships as a
   pre-release. Closes #682, #696, #698, #703, #709, #714, #742, #759.
4. **Event-loop blocking and update churn.** Synchronous python-miio calls run on the event loop,
   `MiotDevice` is created without a mapping (warning spam, #791), and the map keeps refreshing while
   docked (#764) and floods the logbook (#719). Import #775 (skip #769, which it covers). Closes #791,
   #764, #719; check #655 and #601 against it.
5. **Xiaomi map format: decryption key and API choice.** "Incorrect AES key length": the key is
   derived from `model.replace("xiaomi", "mi")` (`vacuum_xiaomi.py`), which is the wrong length for
   names like `xiaomi.vacuum.c107`, and Roborock users who pick the Xiaomi format get the same error.
   Fix the key derivation and warn when the chosen map format does not match the model. Closes #731,
   #732, #733, #763.
6. **Xiaomi models: live data and map index.** Robot position and path missing while cleaning, wrong
   map after maps were deleted, missing walls and no-go zones (b108gl, ov43gb, ov81gl, S40 Pro).
   Import #781 (skip #750, which does the same in 976 lines) and a generalised #748 (ov21gl rooms
   with `room_id=0`, zones, walls; skip #749, wrong base). Closes #720, advances #563, #657, #702,
   #739.

## Later

- **Dreame encrypted maps** ("incorrect header check" on p2140/p2150/r22xx) and Viomi V5 Pro
  (#746, reported on alpha-24). Needs a captured map from a reporter.
- **Roidmi sdj60**: port v2 PR #768 to `vacuum_roidmi.py` (#572).
- **Ijai rendering**: #794 (fit to explored area), without the bundled font if possible.
- **Small imports**: #786 (`as_list_of_dict` with ints) if not folded into the Ijai change; #591 if
  `scripts/` keeps shipping; check #636 (homes without `share_home_list`) against v3 discovery.
- **README for v3 in depth**: options flow, every entity and attribute, and the card integration.
- **Real Home Assistant smoke test**: install the release zip into a Home Assistant container and
  set it up against a recorded cloud, like the card's end-to-end suite.
- **Lint baseline**: widen the ruff rules (pyupgrade, import order, bugbear `B904`) in one dedicated
  change.
- **Undeclared dependency**: `vacuum-map-parser-ijai` imports `google.protobuf` without declaring it;
  decide whether `manifest.json` lists `protobuf` or the parser is fixed.
- **Default HACS listing** once the first stable release is out.

## Feature requests kept

Multi-floor maps (#67, #350), rotation by any angle and trim by coordinates (#137, #377), background
image (#39), carpets and room order (#185), cleaning history map (#633), cloud-only mode without a
local host (#381), RGBA room colours (#652), S40 walls and no-go zones (#739), a notification when
re-authentication is needed (#338, #440).

## Not planned

| Item | Why |
| --- | --- |
| v2 YAML login failures (#157, #422, #533, #583, #629, #644, #645, #697, #752, #753, #760) | v2 is frozen; v3 login replaces it. #697 is covered by the login thread. |
| Other v2-only display and blueprint issues (#20, #71, #75, #173, #236, #339, #351, #426, #462, #463, #487, #504, #507, #514, #536, #539, #540, #547, #562, #605) | Only on the v2 camera platform. |
| Roborock-app-only vacuums (#100, #156, #388, #461, #528) | Those devices are not in the Xiaomi cloud. |
| PR #770 (IJAI/Xiaomi retrieval rewrite) | Changes the encrypted request format for every vendor; the targeted Ijai PRs cover the same bugs. |
| PRs #749, #767, #527, #289 | Wrong base, junk, or superseded by the v3 code. |
