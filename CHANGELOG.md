# Changelog

## Unreleased

First release of this fork under its own name, based on upstream v3.0.0-alpha-24. Existing v3
setups keep working: the integration domain, config entries and entity ids are unchanged.

### Fixed

- Setup no longer aborts with "Unknown error occurred" when the Xiaomi cloud times out while listing
  the devices of one of your homes; that home is skipped.

### Changed

- The integration is named **Better Xiaomi Cloud Map Extractor**, and bugs go to this fork's issue
  tracker.
