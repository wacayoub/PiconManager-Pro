# PiconManager Pro

Modern Enigma2/OpenATV picon manager for Vu+ receivers.

## Current release
- Version: 1.4.0-r0
- Package: `enigma2-plugin-extensions-piconmanagerpro_1.4.0-r0_all.ipk`
- Target: OpenATV / Enigma2
- Sources supported by the plugin: OpenPicons/picons, LyngSat Logo, Chocholousek packs, Global HD fallback, local picons.

## Online installation

Run on the receiver:

```sh
wget -qO- https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/install.sh | sh
```

The installer downloads the current IPK from this repository, verifies its SHA-256 checksum when `sha256sum` is available, installs it with `opkg`, removes the temporary package, and restarts Enigma2.

## Online update

Re-run the same command. The installer always reads `update.json` first, so future versions can be published without changing the receiver command.

## Repository layout

- `install.sh` — network installer/updater
- `update.json` — current release manifest
- `packages/` — installable IPK packages
- `src/` — plugin source
- `tools/` — receiver-side diagnostic helpers

## Important

PiconManager Pro does not declare success when zero picons are applied. Check `/tmp/piconmanagerpro.log` and run `piconmanagerpro-check` for diagnostics.
