# Changelog

## 1.4.1

- Change x4fp mode state order

## 1.4.0

- Add Octo and Open Collector i/o support
- Add X-010V support
- bump pypx800v5

## 1.3.0

- Migrate deprecated methods

## 1.2.0

- Fix global refresh from push. Update your PUSH URL to: `/api/ipx800v5_refresh/on`

## 1.1.0

- No diag sensor anymore, set `diag_sensors` to `True` in yaml config to add them
- Rename default IPX800 entities to match device (duplicate entities can be created, you have to delete the old one)

## 1.0.0

- Stable version
- IPX800V5 5.4.3.1 firmware compatibility

## 0.7.0

- 2022.5 compatibility

## 0.6.0

- 2022.4 compatibility
- Add API call to ask refresh

## 0.5.0

- bump pypx800v5

## 0.4.0

- Add all IPX diagnostic entities
- Add binary sensor for thermostat fault
- bump pypx800v5

## 0.3.1

- Fix device name for objects entities
- Add exceptions handling on setup

## 0.3.0

- /!\ Need Home-Assistant 2021.12 or later
- Handle config auto for yaml
- Fixes and improvments
- Add service to create a configured PUSH object
- Add X-8R long push sensor

## 0.2.0

- Support yaml config

## 0.1.0

- Initial release
