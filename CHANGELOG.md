# Changelog

# [1.9.0](https://github.com/Aohzan/ipx800v5/compare/1.8.4...1.9.0) (2025-04-23)


### Features

* add release ([8a6e40a](https://github.com/Aohzan/ipx800v5/commit/8a6e40a20b0c8e75d09bcf97f987e6976bca3a11))

## 1.8.4

- bump pypx800v5

## 1.8.3

- bump pypx800v5

## 1.8.2

- Fix error when debug logs activated introduced in 1.8.1

## 1.8.1

- Fix error when retrying IPX API request

## 1.8.0

- bump pypx800v5
- Add Access Control support
- Fix deprecated code

## 1.7.1

- Bump pypx800v5 to fix security issue

## 1.7.0

- Remove service for create push automaticaly
- Fix error when a screen was added on the X-Display since the last HA starts
- Fix deprecation warning on climate entities for turn_on/off implementation

## 1.6.4

- Replace deprecated TEMP_CELCIUS constant by Enum

## 1.6.3

- Fix options merging with yaml configuration

## 1.6.2

- Fix X-010V level

## 1.6.1

- Update deprecated code

## 1.6.0

- Add X-Display support

## 1.5.1

- Fix configflow for multiple extension
- Fix ext/obj name matching

## 1.5.0

- /!\ Update entities' unique_id to handle multiple extension, it will recreate your entities, it's recommended to delete this integration configuration before update
- /!\ Update extension and objects number to match IPX800 index, if you use yaml config, you must substract by one all `ext_number` (`1` => `0`)
- Bump pypx800v5 (ping method update)
- Fix devices creation

## 1.4.7

- Fix deviceinfo for extensions
- Fix X-010V auto configuration

## 1.4.6

- Fix deviceinfo via_device property

## 1.4.5

- Bump pypx800v5 to fix missing extensions: X010V and X8D

## 1.4.4

- Fix DeviceInfo for HA 2023.8 release

## 1.4.3

- Fix X4FP climate

## 1.4.2

- Rollback typing for python 3.9 compatibility

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
