# PiconManager Pro

Modern Enigma2/OpenATV picon manager for Vu+ receivers.

## Current online release

- Version: **1.5.1-r0**
- Plugin version: **1.5.1**
- Package: `enigma2-plugin-extensions-piconmanagerpro_1.5.1-r0_all.ipk`
- Size: **39,956 bytes**
- SHA-256: `6c7169b2eb1435da527591b9efa9a1a637166f24f5509354c6542173585634e7`
- Target: OpenATV / Enigma2

## 1.5.1 — LyngSat extraction fix

Version 1.5.1 fixes the case where **LyngSat Logo returned 0 results** even when thousands of receiver channels were scanned.

The LyngSat parser no longer assumes that the channel name and logo image are inside the same HTML table cell. It now:

- follows channel links and logo images in document order;
- pairs adjacent channel/logo cells;
- uses an additional regex fallback for current LyngSat layouts;
- accepts PNG, SVG and WEBP logo URLs;
- normalizes channel names before matching;
- automatically invalidates the old LyngSat cache and rebuilds the index;
- displays the number of LyngSat logos indexed, matches found and channels without a logo.

No manual cache cleanup is required after upgrading from 1.5.0.

## In-app Online Update

From PiconManager Pro:

1. Press **MENU**.
2. Select **Online Update — vérifier GitHub**.
3. The plugin compares the installed version with `update.json`.
4. Confirm the update when **1.5.1-r0** is offered.
5. The package is downloaded from GitHub and verified by size and SHA-256 before installation.
6. Restart Enigma2 when prompted.

## First installation / recovery

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

## Update security

Before `opkg` is allowed to install a downloaded package, PiconManager Pro verifies:

- package size from the GitHub manifest;
- full SHA-256 checksum;
- package/version metadata;
- availability of every multipart payload.

If integrity verification fails, installation is cancelled.

## Repository layout

- `install.sh` — online bootstrap/recovery installer
- `update.json` — official Online Update manifest
- `packages/1.5.1-r0/part01...part15` — verified 1.5.1-r0 package payload
- `packages/1.5.0-r0/` — previous release
- `packages/1.4.0-r0/` — previous release

## LyngSat diagnostics

After selecting **LyngSat Logo**, a successful index now reports:

`LyngSat Logo : <N> logos indexés • <N> correspondances • <N> sans logo`

For troubleshooting, inspect:

```sh
tail -n 100 /tmp/piconmanagerpro.log
```
