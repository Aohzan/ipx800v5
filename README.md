# ipx800v5 integration for Home Assistant

![GitHub release (with filter)](https://img.shields.io/github/v/release/aohzan/ipx800v5) ![GitHub](https://img.shields.io/github/license/aohzan/ipx800v5) [![Donate](https://img.shields.io/badge/$-support-ff69b4.svg?style=flat)](https://github.com/sponsors/Aohzan) [![Marketplace](https://img.shields.io/badge/Marketplace-Default-41BDF5.svg)](https://www.home-assistant.io/integrations/marketplace/)

This a _custom component_ for [Home Assistant](https://www.home-assistant.io/).
The `ipx800v5` integration allows you to get information and control the [IPX800 v5 and its extensions](http://gce-electronics.com/).

![README en français](README.fr.md) :fr:

## Installation

### Marketplace

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=Aohzan&repository=ipx800v5&category=integration)

Settings > Marketplace > search for "GCE IPX800 V5" > Install.

### Manually

Copy `custom_components/ipx800v5` in `config/custom_components` of your Home Assistant (you must have `*.py` files in `config/custom_components/ipx800v5`).

## Configuration

### Easy

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ipx800v5)

Or go to Settings > Devices & services > Add integration and select GCE IPX800 V5. Follow the instructions.

### Advanced

Add the `ipx800v5` key and your full configuration in `configuration.yaml`.
See the ![french README](README.fr.md) for details

## Dependency

[pypx800v5 python package](https://github.com/Aohzan/pypx800v5) (installed by Home-Assistant itself, nothing to do here)
