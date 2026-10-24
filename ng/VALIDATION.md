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

The initial final-package local suite had 31 passing tests. Coverage includes IPTV/private refs,
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

## Approved installation and live display check

The user subsequently approved installation of the exact 34,968-byte IPK above.
`opkg --noaction` offered only NG, and installation completed successfully.
Enigma2 PID was identical immediately before/after installation. Protected files
were identical. No real picon update was performed.

The plugin list was refreshed through the existing local OpenWebif interface,
and NG was opened with the receiver's remote-control API. This exposed a real
dashboard layering defect: decorative labels covered the text widgets. The fix
sets explicit widget/panel z positions and removes a redundant fullscreen label.
A regression test was added; the local suite now has **32 passing tests**.
Only NG's `plugin.py` was corrected on the receiver, with its approved original
saved under NG's plugin-backups directory. No package reinstallation was run.

The user separately approved **one** Enigma2 GUI restart to load the corrected
module. No recording was active. The process changed from PID 850 to 1741, and
the corrected dashboard was opened and visually inspected at 1920x1080 under
Metrix. Labels, nine menu entries, selection focus and footer were visible.
This confirms the FHD dashboard rendering, not all sub-menu interactions.
The receiver subsequently stopped responding to SSH (connection timeout), which
interrupted the remaining live checks. SSH returned, but `/proc/uptime` then
showed a full receiver reboot (about two minutes uptime, Enigma2 PID 1964).
Only one GUI-restart API request was sent by this task; no full-reboot command or
second restart was sent. The cause of the full reboot is unconfirmed. Current
kernel logs contain no preserved explanation and there is no new Enigma2 crash
log. The user was asked whether they restarted the receiver themselves. Treat
stability as unresolved until that is clarified and the remaining live checks
can safely resume. All 1,677 captured bouquet files still match the original
read-only inventory after reconnection (zero changed or missing).

The rebuilt corrected IPK is 34,966 bytes, SHA-256
`f14a5dddb363cad3bda580ce8ad983e252791b6c736274c4258ae8318a6c967a`.
It remains `hardware-validation-required`. Its functional engine is unchanged
from the receiver-tested package; the display-layer regression passed locally
and the corrected installed dashboard was observed live.

A final cache-invalidation fix clears stale catalogue state on rescan so the next
update plan rematches the newly scanned services. Its regression test brings the
suite to 33 tests. The latest IPK (including this fix and the layer correction)
is 34,968 bytes, SHA-256
`07ee2b6105220ba5d07cb7a22e1736f4df06c8bfd34c86bd45fef3ee30463cf7`.
All 33 tests passed on the receiver with this exact latest IPK (1.80 s), including
package decoding/metadata/scope validation and compilation with Python 3.14.7.
Protected-file comparison was identical. NG's corrected runtime source was
aligned on disk with a backup; no additional package installation or restart was
performed. An already imported module will use the new cache behavior only after
the next normal GUI session; no further GUI restart is authorized by this record.

A direct LyngSat page test returned 40 parsed entries. A sample render from the
pinned GitHub `ckat.default.png` did **not** reproduce the original Chocholousek
pixels: original alpha bounds `(8, 68, 391, 171)`, candidate `(8, 70, 392, 169)`.
The example recipe therefore remains unverified and no styled catalogue was
published or applied. Matching canvas dimensions alone is insufficient.

## Remaining release gates

- Resume the interrupted real Enigma2 session: remote navigation,
  focus, color keys, preview rendering, back navigation, and opening/closing all
  screens. GUI contract tests do **not** constitute a real Metrix screen test.
- Live HD and remaining FHD sub-screen checks. The corrected FHD dashboard was
  inspected; no skin/resolution change was performed.
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

## User-requested simplification and persistent offline data

The user requested removal of startup scans and repeated downloads, and a simpler
menu. The revised home has three choices: Mes picons / Mettre à jour / Réglages.
Channel scan is a deliberate Settings action. Startup reads a small persistent
summary; the full inventory is loaded lazily in a worker when browsing picons.
Empty/corrupt cache and changed preferences never silently trigger an analysis.
Download staging reuses SHA-256-verified cached PNGs or previous prepared files;
LyngSat previews and existing catalogue indexes reopen without repeat HTTP.

44 tests passed locally and on the receiver (Python 3.14.7, 2.35 s). These include
reopening twice with scan/HTTP calls forbidden, reopening the local channel view
without the original bouquet file, persisted empty inventory, cache corruption,
explicit refresh, settings context changes, repeated source-preview reuse, reuse
of older staged PNGs, and rejection/refetch of corrupt cached PNGs.

The previous captured inventory was prepared off receiver after rechecking all
1,677 bouquet files against the original capture. Only installed PNG filenames
were read from the receiver; no picon images were downloaded or modified.
The compressed inventory has 107,252 entries and occupies 6,280,419 bytes. NG's
sources and cache were updated with a backup under `plugin-backups`; no opkg
reinstall occurred. Summary-only startup measured 6.37 / 4.68 / 4.62 ms, with zero
service rows loaded and scan/network functions patched to fail on unexpected use.
The Enigma2 PID remained 4918. The 44-test hardware run also confirmed unchanged
protected files.

The current IPK is 37,386 bytes, SHA-256
`f9c18674e0a78819913215d63adc9e962b92c3acc80b2ae2a38d66518df835c5`.
The user declined activation now: “Pas maintenant, garder Enigma2 en cours”.
The existing session still uses previously imported code. No restart/reboot or
forced reload was performed for this correction. The simplified UI awaits a
future GUI session the user chooses. Style calibration and the earlier stability
question remain open; the official release is unchanged.

## Direct navigation, satellite groups, and native screen exit correction

The user requested direct self-testing and grouping by satellite. The installed
simplified home was now observed live at 1920×1080 under Metrix. It displayed
107,252 saved services and 10,999 installed picons. Remote navigation confirmed
the current picon preview, movement between rows/pages, and the present/missing
filters (10,999 and 96,253 entries). No scan or download was requested on entry.

Leaving the browser revealed an actual Python error at Screen.deleteGUIScreen:
`TypeError: 'list' object is not callable`. Inspection of the receiver's compiled
Screen methods confirmed that destruction calls self.items(). Browser had assigned
its row list to that same attribute. Row data is now called entries throughout
the GUI and callbacks. Tests include destruction, not just geometry/navigation.
Enigma2 automatically recovered during this test (PID 7851 → 8676). No restart or
reboot command was issued. This new, specific failure does not establish the cause
of the earlier unexplained full receiver reboot.

The new grouping engine was run in a disposable Python process on the receiver
against its real saved inventory. It identified 40 satellite positions and a
separate IPTV group (94,512 services). All per-group totals, found and missing
counts reconcile with the original inventory. Namespace transponder bits are
ignored when grouping, and IPTV with borrowed DVB IDs remains IPTV. Original PNG
samples and protected files were unchanged; the Enigma2 PID was unchanged during
this separate engine run. Peak process RSS including the full inventory and
online probe was 115.3 MiB. First full inventory load/grouping took 9.68 seconds;
the repeated in-memory grouping took 0.016 ms.

To avoid that full read merely to display satellite choices, group counters now
live in the small saved inventory summary. The existing summary was populated from
the verified grouping result, without another bouquet analysis. After copying the
corrected sources with an NG backup, initialization plus group-list retrieval took
133.43 ms with zero full-inventory rows loaded and load_inventory patched to fail.
The Enigma2 PID remained 8676 and protected files were unchanged.

The GitHub selection probe fetched the pinned upstream index for one real satellite
and reopened its selection cache with HTTP forbidden. It correctly stopped at the
unavailable exact-style PNG manifest. The online logo-update path therefore is
**not validated end to end**. No original picon replacement was performed.

52 tests passed locally and on Python 3.14.7 on the receiver (5.01 seconds for the
hardware suite). Three further checks executed the receiver's actual compiled
Screen.deleteGUIScreen/doClose methods against candidate Browser components in an
isolated interpreter. All closed cleanly. Protected files matched before/after.
The current IPK is 39,496 bytes, SHA-256
`14b8f63ff171e599ef2a9fc95ea05028f2cef89cd3fc87443ac397759bf672ee`.
It remains hardware-validation-required.

No forced module reload or package reinstall was performed. The running Enigma2
session predates the final source copy. The corrected exit behavior and new
satellite screens still need live session validation after a user-chosen GUI
restart. The user's refusal to restart now remains in force. Do not label this
release stable or replace official 1.5.1 until the outstanding display/style/
transaction gates pass.

## Accepted usability improvements and successful live exit check

The user accepted favorites, remembered position, guided updates, side-by-side
preview, quick undo and readable progress. These are implemented without adding
home-menu entries. Blue toggles favorites in group choices; reordering retains
selected group identities. Navigation persists independently of the inventory.
Missing picons sort first and are selected by default; installed fallback picons
are also excluded in missing-only mode. Each apply/undo still needs confirmation.
Quick undo selects the newest committed batch for the destination using durable
commit timestamps and rejects a stale confirmation. Previous integrity, external
change, recovery and source/style checks remain in place.

Before applying these additions, the previously loaded satellite UI was tested
directly at 1920×1080 in the receiver's current FHD session. A satellite channel
list and an original picon preview were observed. Exiting returned cleanly through
the satellite list, NG home and plugin browser. The PID remained 16589. This
confirms the earlier native Screen.items() fix in a live session; it does not
validate the new favorites/side-by-side screen in that session. No restart or
reboot command was sent and no skin setting was changed.

59 tests passed locally and on the receiver's Python 3.14.7 (5.59 seconds), plus
three native compiled Screen destruction checks. New coverage includes persisted
favorites and position without cache invalidation, retained group selection after
favorite reordering, restored page/focus, coalesced progress, fallback preservation,
commit-order undo and rejection of stale confirmation. A synthetic GUI workflow
uses real transactions and PNGs to test missing-only proposal/selection, preview,
refused and accepted apply, refused and accepted undo, and original preservation.
All transaction writes in these checks were in disposable test directories.

The receiver had a legacy refreshed inventory with no group summary. Migration
added only group metadata from existing saved rows, preserving the scan date,
original compressed row file and other NG data. It does not scan bouquets or use
HTTP. Next initialization plus group retrieval took 698.33 ms with zero service
rows loaded, with load_inventory patched to fail. Five NG source files were
backed up and copied with matching hashes; PID 16589 and protected files were
unchanged. No package reinstall or forced import reload was performed.

The current IPK is 41,484 bytes, SHA-256
`26a01e61f46e5f471e740ef388940e70d30cdadb201a676d3e7b0a22f1f313bb`.
It remains hardware-validation-required. The new additions are stored on disk
and need live visual validation in a later GUI session chosen by the user.

The bounded off-host style check on the available upstream PNG candidates still
failed: kapatid alpha bounds were (8,48,391,192) for the original versus
(8,48,392,192) for the candidate; ckat also remained unequal. No approximate
catalogue was published, and no installed artwork was replaced. Exact Chocholousek
calibration and end-to-end approved production update/undo remain open.
