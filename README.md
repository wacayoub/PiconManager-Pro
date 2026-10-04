# PiconManager Pro

Modern Enigma2/OpenATV picon manager for Vu+ receivers.

## Current online release

- Version: **1.5.0-r0**
- Plugin version: **1.5.0**
- Package: `enigma2-plugin-extensions-piconmanagerpro_1.5.0-r0_all.ipk`
- Size: **38,626 bytes**
- SHA-256: `fc273972376b227f3c0c9c08c217dd960fbcc9e4674d44cab31c2b45db49c971`
- Target: OpenATV / Enigma2

## New in 1.5.0 — In-app Online Update

PiconManager Pro can now update itself directly from GitHub.

On the receiver:

1. Open **PiconManager Pro**.
2. Press **MENU**.
3. Select **Online Update — vérifier GitHub**.
4. The plugin compares the installed version with `update.json`.
5. If a newer version exists, confirm the installation.
6. The package is downloaded from GitHub, its size and SHA-256 are verified, then it is installed with `opkg`.
7. PiconManager Pro asks whether Enigma2 should be restarted.

No PC, phone transfer, FTP, USB or manual `/tmp` copy is required after version 1.5.0 is installed.

## First installation / upgrade from 1.4.0

Version 1.4.0 does not yet contain the in-app updater, so upgrade to 1.5.0 once with:

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

After that, future updates are available directly inside PiconManager Pro through **MENU → Online Update**.

## Online installer

The same command can always be used as a recovery or first-install method:

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

The installer reads the same GitHub `update.json` channel used by the application.

## Update security

Before `opkg` is allowed to install a downloaded package, PiconManager Pro verifies:

- package size from the GitHub manifest;
- full SHA-256 checksum;
- package/version metadata;
- download availability, with a GitHub multipart fallback.

If the size or checksum does not match, installation is cancelled.

## Repository layout

- `install.sh` — online bootstrap/recovery installer
- `update.json` — official online-update manifest
- `packages/1.5.0-r0/part01...part09` — verified 1.5.0-r0 package payload
- `packages/1.4.0-r0/` — previous release fallback
