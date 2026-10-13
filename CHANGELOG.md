# Changelog

## [2.2.0](https://github.com/Aohzan/ipx800v5/compare/2.1.1...2.2.0) (2026-10-13)

### Features

* add device classes to reboot, AC power and fault entities ([104a9d8](https://github.com/Aohzan/ipx800v5/commit/104a9d85e5c7cb010b75024141a4d9a1661d5e67))
* add X-400 CT and X-400 Ana sensors ([ceed812](https://github.com/Aohzan/ipx800v5/commit/ceed81254d1c232351afb2f0fcb90181975ae58b)), closes [#21](https://github.com/Aohzan/ipx800v5/issues/21)
* record long-term statistics for IPX800 analog inputs ([6b87441](https://github.com/Aohzan/ipx800v5/commit/6b874413cd0beae8c123125ce45c3446bdbad018))
* support cooling thermostats ([09dbecc](https://github.com/Aohzan/ipx800v5/commit/09dbecc108687e123c0d64a62c11b044aa052543)), closes [#26](https://github.com/Aohzan/ipx800v5/issues/26)

### Bug Fixes

* apply options flow changes to UI entries ([e4e99e6](https://github.com/Aohzan/ipx800v5/commit/e4e99e6fab89cedf5b621f73d6d56842b180cc2e))
* **deps:** bump pypx800v5 to 1.4.4 ([e7bf4f4](https://github.com/Aohzan/ipx800v5/commit/e7bf4f42d4ada2f1bb67428f50cf7a8bfab210f1))
* index X-Display screens with the int screen id ([34eb54f](https://github.com/Aohzan/ipx800v5/commit/34eb54fa9a75b5b467030655e0b1651b559b027e))
* keep entity attributes defined by entity classes ([238731f](https://github.com/Aohzan/ipx800v5/commit/238731fdf82a6251f7d54023edf2ff935f20e1e5))
* keep entry data when unloading platforms fails ([9f10a79](https://github.com/Aohzan/ipx800v5/commit/9f10a79b887f1f6771ea19d6a3fa91854dc8339a))
* keep push endpoints working after an entry reload ([48c1d82](https://github.com/Aohzan/ipx800v5/commit/48c1d8227058e11bd6ee05bb2782e0173a0d33bf))
* link extension devices to the IPX800 with via_device_id ([0bf1906](https://github.com/Aohzan/ipx800v5/commit/0bf1906987b7904c54848cc5c0311cfc993e7c19))
* read the access control last code from polled values ([631432c](https://github.com/Aohzan/ipx800v5/commit/631432cacf1d00dfc7988d4f8d98c0f1d6348ffb))
* reject malformed push requests instead of failing ([1676bca](https://github.com/Aohzan/ipx800v5/commit/1676bca2f6c30f6a2e0d6b4fef56a40329d4cd01))
* retry setup when the IPX800 is unreachable ([d7c5975](https://github.com/Aohzan/ipx800v5/commit/d7c59756ce41a6ab00e05e5c34224f50e7c8046b))
* scope extension device identifiers by IPX800 ([d41f11d](https://github.com/Aohzan/ipx800v5/commit/d41f11d25887547c473dac649167f7ee2fede20b))
* show saved X-8R relay types in options flow ([1356e79](https://github.com/Aohzan/ipx800v5/commit/1356e794de58150655adaac7ead0442fc6541d70))
* stop advertising light transitions ([3ca7aa0](https://github.com/Aohzan/ipx800v5/commit/3ca7aa08906e07ad91fbdaef7f7fce6ff72f2b16))
* turn on X-PWM RGB lights at the default brightness ([63349f0](https://github.com/Aohzan/ipx800v5/commit/63349f05eed8e6a23e86b2baa8566aa4646d643b))
* update number and select states after a change ([e1079d3](https://github.com/Aohzan/ipx800v5/commit/e1079d3725a2cdfa8784c5365d6bd83c76a4b9ca))
* use via_device instead of deprecated device registry lookup ([bd1952e](https://github.com/Aohzan/ipx800v5/commit/bd1952eebe914c2104a9d6f96573cfd2108ca0a7)), closes [#40](https://github.com/Aohzan/ipx800v5/issues/40)

### Performance Improvements

* don't request a refresh when adding coordinator entities ([555cfbe](https://github.com/Aohzan/ipx800v5/commit/555cfbeeab365304bbb06a63fa234e55e3679a95))

## [2.1.1](https://github.com/Aohzan/ipx800v5/compare/2.1.0...2.1.1) (2026-09-09)

### Bug Fixes

* device registry depreciation ([eea7391](https://github.com/Aohzan/ipx800v5/commit/eea7391cd333fb78a17ba7f43785eecf1a38f3e9))

## [2.1.0](https://github.com/Aohzan/ipx800v5/compare/2.0.1...2.1.0) (2026-05-12)

### Features

* add configurable temperature parameters for the thermostat object ([67dd380](https://github.com/Aohzan/ipx800v5/commit/67dd3809928b1a87956808a8fdf7b531d4ee37c0))

## [2.0.1](https://github.com/Aohzan/ipx800v5/compare/2.0.0...2.0.1) (2026-05-10)

### Bug Fixes

* warning when reboot ipx ([aa8f230](https://github.com/Aohzan/ipx800v5/commit/aa8f2306148490b27756be7e4a3716f8e6fbdc5d))

## [2.0.0](https://github.com/Aohzan/ipx800v5/compare/1.9.5...2.0.0) (2026-05-04)

### ⚠ BREAKING CHANGES

* check logs to know which URL use

### Features

* add extra attributes to easily identify where is physically located the entity ([9ddc0b6](https://github.com/Aohzan/ipx800v5/commit/9ddc0b6e0c0666b91abf2228a2a2504d44e40345))
* remove deprecated push api url ([a14d6d7](https://github.com/Aohzan/ipx800v5/commit/a14d6d76df0be00087ca781ae510ee6cd832d5f9))

## [1.9.5](https://github.com/Aohzan/ipx800v5/compare/1.9.4...1.9.5) (2026-01-30)

### Bug Fixes

* remove URL from translations files ([8b95b12](https://github.com/Aohzan/ipx800v5/commit/8b95b120724b4c07bf1f2a8e030d4d6ce54f733f))

## [1.9.4](https://github.com/Aohzan/ipx800v5/compare/1.9.3...1.9.4) (2025-10-17)

### Bug Fixes

* revert 1.9.3 changes ([d1b5551](https://github.com/Aohzan/ipx800v5/commit/d1b5551250e197ce545b4f44c3c39e320315d5a9))

## [1.9.3](https://github.com/Aohzan/ipx800v5/compare/1.9.2...1.9.3) (2025-10-14)

### Bug Fixes

* bump pypx800v5 to fix xdimmer turn off ([9fcbf9b](https://github.com/Aohzan/ipx800v5/commit/9fcbf9b1543e949624a586df7dc8c180cc6ee9be))

## [1.9.2](https://github.com/Aohzan/ipx800v5/compare/1.9.1...1.9.2) (2025-05-08)

### Bug Fixes

* auth handle on API ([efb7d3a](https://github.com/Aohzan/ipx800v5/commit/efb7d3ae1404f9535ab071f4622a3daaa76caa63))
* multiple IPX push ([f9bec0d](https://github.com/Aohzan/ipx800v5/commit/f9bec0d4feba5570ea8b63c5251fc74e7f4a6af9))

## [1.9.1](https://github.com/Aohzan/ipx800v5/compare/1.9.0...1.9.1) (2025-04-23)

### Bug Fixes

* deprecated optionsflow config ([7d13044](https://github.com/Aohzan/ipx800v5/commit/7d130443543544e0e6c7c42b073eea7bf79657bd))

## [1.9.0](https://github.com/Aohzan/ipx800v5/compare/1.8.4...1.9.0) (2025-04-23)

### Features

* add release ([8a6e40a](https://github.com/Aohzan/ipx800v5/commit/8a6e40a20b0c8e75d09bcf97f987e6976bca3a11))

## 1.8.4

* bump pypx800v5

## 1.8.3

* bump pypx800v5

## 1.8.2

* Fix error when debug logs activated introduced in 1.8.1

## 1.8.1

* Fix error when retrying IPX API request

## 1.8.0

* bump pypx800v5
* Add Access Control support
* Fix deprecated code

## 1.7.1

* Bump pypx800v5 to fix security issue

## 1.7.0

* Remove service for create push automaticaly
* Fix error when a screen was added on the X-Display since the last HA starts
* Fix deprecation warning on climate entities for turn_on/off implementation

## 1.6.4

* Replace deprecated TEMP_CELCIUS constant by Enum

## 1.6.3

* Fix options merging with yaml configuration

## 1.6.2

* Fix X-010V level

## 1.6.1

* Update deprecated code

## 1.6.0

* Add X-Display support

## 1.5.1

* Fix configflow for multiple extension
* Fix ext/obj name matching

## 1.5.0

* /!\ Update entities' unique_id to handle multiple extension, it will recreate your entities, it's recommended to delete this integration configuration before update
* /!\ Update extension and objects number to match IPX800 index, if you use yaml config, you must substract by one all `ext_number` (`1` => `0`)
* Bump pypx800v5 (ping method update)
* Fix devices creation

## 1.4.7

* Fix deviceinfo for extensions
* Fix X-010V auto configuration

## 1.4.6

* Fix deviceinfo via_device property

## 1.4.5

* Bump pypx800v5 to fix missing extensions: X010V and X8D

## 1.4.4

* Fix DeviceInfo for HA 2023.8 release

## 1.4.3

* Fix X4FP climate

## 1.4.2

* Rollback typing for python 3.9 compatibility

## 1.4.1

* Change x4fp mode state order

## 1.4.0

* Add Octo and Open Collector i/o support
* Add X-010V support
* bump pypx800v5

## 1.3.0

* Migrate deprecated methods

## 1.2.0

* Fix global refresh from push. Update your PUSH URL to: `/api/ipx800v5_refresh/on`

## 1.1.0

* No diag sensor anymore, set `diag_sensors` to `True` in yaml config to add them
* Rename default IPX800 entities to match device (duplicate entities can be created, you have to delete the old one)

## 1.0.0

* Stable version
* IPX800V5 5.4.3.1 firmware compatibility

## 0.7.0

* 2022.5 compatibility

## 0.6.0

* 2022.4 compatibility
* Add API call to ask refresh

## 0.5.0

* bump pypx800v5

## 0.4.0

* Add all IPX diagnostic entities
* Add binary sensor for thermostat fault
* bump pypx800v5

## 0.3.1

* Fix device name for objects entities
* Add exceptions handling on setup

## 0.3.0

* /!\ Need Home-Assistant 2021.12 or later
* Handle config auto for yaml
* Fixes and improvments
* Add service to create a configured PUSH object
* Add X-8R long push sensor

## 0.2.0

* Support yaml config

## 0.1.0

* Initial release
