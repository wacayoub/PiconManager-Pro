# PiconManager Pro

Modern Enigma2/OpenATV picon manager for Vu+ receivers.

## Current online release

- Version: **1.4.0-r0**
- Package: `enigma2-plugin-extensions-piconmanagerpro_1.4.0-r0_all.ipk`
- Size: **36,916 bytes**
- SHA-256: `8f7fd60e957e8a0219ffb4586839aaad5b1f2a4787c2fcaaa3ffc46cbdfae48d`
- Target: OpenATV / Enigma2

## Install directly from GitHub

Run this command on the receiver:

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

No manual IPK transfer is required.

The installer:
1. downloads `update.json` from GitHub;
2. downloads the current IPK directly from GitHub;
3. checks package size and SHA-256;
4. installs or updates with `opkg`;
5. runs `piconmanagerpro-check` when available;
6. restarts the Enigma2 GUI.

If the direct IPK URL cannot be downloaded, the installer has a GitHub-hosted multipart fallback.

## Online update

Use the same command again:

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

Future releases only require updating `update.json` and publishing the new package. The receiver-side command stays the same.

## Install without automatic GUI restart

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | PICONMANAGERPRO_NO_RESTART=1 sh
```

## Repository layout

- `install.sh` — online installer/updater
- `update.json` — release manifest
- `packages/enigma2-plugin-extensions-piconmanagerpro_1.4.0-r0_all.ipk` — direct install package
- `packages/1.4.0-r0/part01...part09` — verified fallback copy

## Diagnostics

After installation:

```sh
piconmanagerpro-check
```

PiconManager Pro should not report a successful application when zero picons were actually applied.
