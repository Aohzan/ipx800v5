# ipx800v5 integration for Home Assistant

![GitHub release (with filter)](https://img.shields.io/github/v/release/aohzan/ipx800v5)
 ![GitHub](https://img.shields.io/github/license/aohzan/ipx800v5)
 [![Donate](https://img.shields.io/badge/$-support-ff69b4.svg?style=flat)](https://paypal.me/bstevensondev) [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

This a _custom component_ for [Home Assistant](https://www.home-assistant.io/).
The `ipx800v5` integration allows you to get information and control the [IPX800 v5 and its extensions](http://gce-electronics.com/).

![README en français](README.fr.md) :fr:

## Installation

### HACS

HACS > Integrations > Explore & Add Repositories > GCE IPX800 V5 > Install this repository

### Manually

Copy `custom_components/ipx800v5` in `config/custom_components` of your Home Assistant (you must have `*.py` files in `config/custom_components/ipx800v5`).

## Configuration

### Easy

Add the integration `GCE IPX800V5` in the interface on `Configuration` > `Integration`. Follow the instructions.

### Advanced

Add the `ipx800v5` key and your full configuration in `configuration.yaml`.
See the ![french README](README.fr.md) for details

## Dependency

[pypx800v5 python package](https://github.com/Aohzan/pypx800v5) (installed by Home-Assistant itself, nothing to do here)
