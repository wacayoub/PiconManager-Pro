# PiconManager NG 2027 — Codex handoff

## Objective
Modernize existing `wacayoub/PiconManager-Pro` into PiconManager NG 2.x. Use branch `dev/piconmanager-ng-v2`, target Vu+ Zero 4K, OpenATV 8.0.1, Python 3.

**The plugin UI is Neo Dark. The picons themselves MUST keep the user's current Chocholousek style, pixel-consistent once an original sample has been captured.**

## Existing progress
- `ng/source/PiconManagerNG/plugin.py`: initial Neo Dark 1280×720 / 1920×1080 read-only UI
- `ng/source/PiconManagerNG/core.py`: bouquet scan and SAT SRP recognition; IPTV mapping pending
- `ng/source/PiconManagerNG/updates.py`: checksum verification, staged update/backups prototype; interruption recovery still to validate
- `ng/tests/`: 5 offline tests passed locally
- `main` still contains official v1.5.1; do not replace until real receiver tests have passed.

## Features to finish in one concentrated implementation
1. Neo Dark: minimal fast dashboard, channels / found / missing, scan, source status, preview, visual profile, settings, backups, diagnostics. Proper selection focus and color keys. No inert menu items in production. Test both HD and FHD including Metrix.
2. Keep previous PiconManager Pro v1.5.1 useful features (especially LyngSat, verified GitHub update/installer). Inspect existing package/source first, preserve configuration where possible.
3. Chocholousek style calibration: find currently installed PNGs; detect profile and measure dimensions, padding, transparency, reflection and style. Do not change original design. New logos must be rendered in matching style (off receiver).
4. Catalogue: `https://github.com/picons/picons` (GPL-3.0). Use up-to-date `srp.index`, `utf8snp.index`, source logos and release metadata. Validate attribution/redistribution rights. Do the heavy SVG/PNG conversion with CI or off receiver; receiver only downloads selected verified PNGs.
5. Matching: exact SRP > verified aliases > normalized UTF8 name > manual choice; handle SAT, IPTV (including Enigma2 4097/5001 and private refs), radio, multiple providers and ambiguous names.
6. Real updates: dry-run, before/after preview, selective incremental downloads, SHA-256, matching style ID, backup, atomic apply with durable journal, restoration after interruption. No silent overwrites.
7. Performance: minimal RAM, no blocking HTTP on GUI, keep caching compact, download only the bouquet's required picons.
8. Tests: a small focused offline suite, then one full hardware check. Do not multiply unnecessary beta/release cycles.

## Direct Codex → Vu+ SSH
- Run Codex on a host that has LAN/VPN access to the receiver. Cloud machines may not reach a private LAN IP.
- Receive host/user from the chat or a local environment variable. Use SSH-agent or local secrets; NEVER publish passwords, keys, tokens or IP addresses in the public GitHub repo.
- Verify SSH host identity. DO NOT disable strict host-key checks or run untrusted install scripts.
- Start read-only: identify image/Python, installed plugin package, /usr/share/enigma2/picon and alternatives, free storage, current Chocholousek picon sample, and whether the old plugin is active.
- No changes to bouquets, IPToSatPro, EPGManager, or other plugins. Do not restart Enigma2 until it is safe and requested.
- Once package is ready and user has approved installation: build an IPK, verify SHA256, take backup, install/test on receiver, validate UI and SAT/IPTV mappings, backup/restore, then supersede old official v1.5.1 on `main`.
- If SSH is unavailable, complete and commit safe offline changes; report the exact network/auth blocker rather than claiming connected.

## Definition of done
Neo Dark GUI stable on Vu+, same Chocholousek icon style, selective up-to-date GitHub catalogue, useful preview, reversible replacement, correct SAT/IPTV mapping, integrity-checked release. No other plugins touched.

## Continuation — 2026-10-24

Read [VALIDATION.md](VALIDATION.md) and the updated [NG README](README.md) before
continuing. The initial prototype has been replaced by functional Neo Dark views,
streaming selective matching, preserved LyngSat parsing/source preview, strict
style verification, durable staged transactions, restoration/recovery, and a
deterministic IPK builder. The local suite now has 31 tests.

Direct SSH with an existing local key and strict host-key verification worked.
The receiver was inspected read-only and the engine was tested in disposable
temporary directories. It runs Python 3.14.7. The active 400x240 transparent pack
is Chocholousek; a second pack has different padding and must not be substituted.
The full inventory has 107,252 services. Measured scan time fell from 127 to 67 s.
No Enigma2 restart, official package replacement or real picon update occurred.

The IPK is prepared with status `hardware-validation-required`, not stable.
Installation was explicitly approved and succeeded without restart. A discovered
dashboard layer defect was corrected in NG's own plugin.py with a backup; no
package reinstall occurred. A separate single GUI restart was explicitly approved
and completed, and the corrected FHD dashboard was visually inspected under
Metrix. The receiver then stopped responding to SSH, interrupting further live
checks. Do not repeat the restart without new approval. The local suite now has
32 tests; 31 engine/package tests previously passed on the receiver. See the full
validation record for the approved and corrected package checksums.
GUI geometry/component tests are not real HD/FHD Metrix display tests.
Exact rendering calibration is still unproven, so no styled public PNG catalogue
has been generated or claimed. Do not bypass this gate or label the release final.
All receiver addresses, credentials, original images and bouquet data stay local.
