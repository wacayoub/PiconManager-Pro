# PiconManager NG 2.0.0 — validation record

## Confirmed on 2026-10-24

The complete original handoff was read. Development remains on
`dev/piconmanager-ng-v2`. The official 1.5.1 update manifest, installer and package
payloads are unchanged. Credentials, receiver address, bouquet contents and
original Chocholousek PNGs are retained only in the ignored local work directory.

SSH used an existing local identity with strict host-key verification. The receiver
reports Vu+ Zero 4K, OpenATV 8.0.1 build 20261003, ARMv7 and Python 3.14.7.
MetrixHD/skin.MySkin.xml is configured. Pillow 12.3.0 is available.

The configured picon destination is `/usr/share/enigma2/picon`, containing 47,243
PNGs. PNG artist metadata confirms Chocholousek authorship. The separate `/picon`
pack contains 23,052 PNGs with different padding; it is not substituted for the
active artwork. Both use 400 × 240 canvases. Original sample pixels, metadata,
alpha bounds and checksums were captured locally without changing the originals.

The engine was executed from an automatically removed temporary directory on the
receiver, with no plugin installation or Enigma2 restart. Results:

| Check | Result |
| --- | --- |
| Initial engine regression suite | 20 passed, 0.86 s |
| Optimized engine and GUI-contract suite | 23 passed, 1.30 s |
| Final package and regression suite, Python 3.14.7 | 31 passed, 1.92 s |
| Reachable distinct services | 107,252 |
| SAT / IPTV | 12,740 / 94,512 |
| Installed / missing in chosen destination | 10,999 / 96,253 |
| GitHub catalogue matches / ambiguities | 10,967 / 42 |
| Pinned upstream revision | `a4c606b91d23338c1c49c44f47b93fc8c5bca2e9` |
| Full scan, before / after parse optimization | 127.25 / 67.15 s |
| Fetch and match selected index entries | 17.66 s |
| Peak process RSS including UI-contract test fixtures | 101.4 MiB |
| Protected files before / after optimized hardware check | identical |

Protected-file comparison included bouquets, Enigma2 settings and IPToSatPro /
EPGManager files. No commands were issued to modify these areas. Tests of writes,
rollback and interruption recovery used temporary synthetic picons only.

The final local suite has 31 passing tests. Coverage includes IPTV/private refs,
lamedb names, reachable bouquets, ambiguity/manual choices, LyngSat split cells,
HD/FHD widget bounds and keyboard navigation, pagination with 100,000 rows,
PNG/checksum failures, stale previews, new-file removal on undo, corrupt backups,
simulated power loss and recovery, IPK path scope, forbidden maintainer scripts,
revision updates and reproducible package output.

The same final 31-test suite passed on the receiver. The actual IPK was decoded,
its package metadata and file scope were validated, and all shipped Python
sources compiled with the receiver's Python 3.14.7. Its size is 34,968 bytes and
SHA-256 is `7248a4e8408e0ebfa31c77f0290ae9e6811c608888be8ea6a81e9b3e630a9c9e`.
Protected files were identical before/after this final temporary-directory run.

## Remaining release gates

- Installation approval, followed by a real Enigma2 session: remote navigation,
  focus, color keys, preview rendering, back navigation, and opening/closing all
  screens. GUI contract tests do **not** constitute a real Metrix screen test.
- Live HD and FHD display checks; no skin/resolution change or GUI restart has
  been performed by this task.
- Complete and prove the exact Chocholousek rendering recipe against original
  samples. Dimensions/transparency alone do not prove identical styling.
- Generate and host the selected GPL-attributed PNG catalogue only after that
  calibration passes. No working styled public catalogue is claimed today.
- End-to-end real catalogue selection, preview, application and restoration on
  the receiver after approval. Synthetic transaction tests already pass.
- Mark a release stable and prepare the official 1.5.1 replacement only when all
  of the above are verified. The NG online updater refuses non-stable releases.

An installable `2.0.0-r0` IPK is produced under `dist/`, together with its SHA-256
and `release.json`. Its status is deliberately `hardware-validation-required`.
It installs only into the PiconManagerNG plugin directory and contains no
maintainer scripts, automatic plugin removal or automatic restart.
