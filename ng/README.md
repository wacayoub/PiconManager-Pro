# PiconManager NG 2.x

Branch: `dev/piconmanager-ng-v2`. Target: Vu+ Zero 4K, OpenATV 8.0.1 / Python 3.
Version: 2.0.0-r0, prepared for hardware validation. Official 1.5.1 is preserved.
See [VALIDATION.md](VALIDATION.md) for measured results and remaining release gates.

## Implemented

- Simple home menu: **Mes picons**, **Mettre à jour**, **Réglages**. Backup,
  manual channel refresh and advanced tools stay inside Settings.
- Mes picons opens a local list of satellite positions, with IPTV in a separate
  group. Position names come from the receiver's satellites.xml. Group counters
  are saved with the inventory so this list does not load all channels. Choose
  a group to browse its current/missing picons. The home menu stays unchanged.
- **Blue marks/unmarks a favorite** in the group list. Favorites appear first;
  the last opened position is focused on the next visit. Navigation preferences
  are saved separately, so they do not invalidate the inventory or trigger a scan.
- Mettre à jour first offers the same groups: OK selects one or more positions,
  then green checks only that selection. Matching and replacement planning are
  restricted to those services. Each selection retains its own offline catalogue
  cache. This follows the position-selection principle used by
  [Chocholousek Picons](https://github.com/s3n0/e2plugins/tree/master/ChocholousekPicons).
- No automatic scan or HTTP at startup. Read a small saved summary; lazily load
  the local channel inventory only when opening Mes picons. A manual refresh is
  available at Réglages → Actualiser mes chaînes. No scan is silently triggered
  by an empty cache, changed preferences or a failed network connection.
- Persist the channel inventory across plugin closes and GUI restarts as a
  compressed local snapshot. Existing installed PNGs stay available offline.
  Verified downloads, older staged PNGs and LyngSat previews are reused instead
  of being downloaded on every visit. Corrupt cached images are rejected.
- Neo Dark dashboard and paginated channel/installed/missing views, native focus,
  remote navigation and color keys, separate HD and FHD geometries.
- Channel labels are formatted for the visible page only, including large IPTV
  groups. Browser data does not shadow the native Screen.items() lifecycle method.
- Workers for scanning, network, downloads and transactions; no GUI-thread HTTP.
- Reachable TV/radio bouquet traversal and lamedb4/5 names. SAT, cable, terrestrial,
  4097/5001/5002/private IPTV refs, namespace/type fallback and Unicode SNP lookup.
  IPTV URL credentials are discarded after parsing; persisted aliases use hashes.
- Streaming GitHub srp.index / utf8snp.index readers pinned to one upstream commit.
  Only relevant mappings are retained; ambiguous matches require a manual choice.
- Preserved 1.5.1 LyngSat parser, including split-cell and document-order fallback,
  per-letter caching, diagnostics and source PNG/WebP preview. Source SVG rendering
  and generation of styled replacement logos belong on the build host.
- Profile capture from original pixels, selective dry-run, staged before/after
  preview, explicit application, SHA-256 and decoded PNG checks, durable preimages
  and journal, atomic file replacement, undo and interruption recovery.
- Guided update: choose groups, inspect proposals, prepare selected picons, compare
  the current logo on the left with the new one on the right, then confirm. Missing
  picons are proposed first and selected by default; replacements require an
  explicit choice. Existing SNP/namespace-fallback picons are also protected by
  the missing-only mode. Preparation, application and undo show current counts.
- **Réglages → Annuler la dernière mise à jour** restores the latest applied batch
  for the chosen destination, including removal of new files. The same action is
  available with blue after applying a preview. It asks for confirmation and
  refuses stale confirmations or external file changes. Older backups remain in
  Réglages → Plus d’options → Sauvegardes.
- Missing-only default. Updates to existing files require a deliberate setting and
  per-batch confirmation. Interrupted operations block new staging until restored.
- Verified online NG plugin package download/installation with code backup and
  explicit confirmation. No forced install and no automatic Enigma2 restart.

## Build and tests

```sh
python -m pip install 'Pillow>=12,<13'
PYTHONPATH=ng/source python -m unittest discover -s ng/tests -v
python ng/tools/build_ipk.py
```

On PowerShell, set `$env:PYTHONPATH='ng/source'` before running unittest.
CI exercises Python 3.12 and 3.14 and uploads the validated IPK/checksum artifact.
The deterministic builder needs only the standard library. It checks that the
package has no maintainer scripts and writes only to the NG plugin directory.

The IPK has a separate package name, `enigma2-plugin-extensions-piconmanagerng`,
so validation does not implicitly remove the official plugin. Installation still
requires the user's approval. Data lives in `/var/lib/piconmanager-ng`; legacy
configuration and state are preserved. Existing configured Enigma2 picon paths
are read; this plugin does not rewrite Enigma2 settings or bouquets.

The persistent cache is stored under `cache/inventory` and `cache/picons` in
the NG data directory. Inventory snapshots are specific to the chosen picon path
and TV/radio preference. Their summary shows when the list was last refreshed.
Without a saved inventory, the plugin asks for the explicit Settings refresh;
it never starts a scan merely because a user opens the plugin or a page.
Catalogue indexes and LyngSat pages remain reusable without time-based automatic
downloads. **Mettre à jour** explicitly checks GitHub; when offline, compatible
previously saved metadata remains available, and PNG integrity/style checks still
apply. A missing or uncalibrated public catalogue is not bypassed by this cache.
Legacy inventory summaries acquire their group counters once from saved rows;
the migration preserves the scan date and never parses bouquets. Navigation is
stored in `navigation.json` under the NG data directory.

Runtime dependencies include `python3-compression` for saved inventory snapshots.

## Exact Chocholousek style and catalogue generation

The active original artwork is authoritative. `/picon` and
`/usr/share/enigma2/picon` may contain visibly different packs even when both are
400x240 transparent. Capturing the profile records evidence; it does not declare
an approximate rendering recipe correct. The example recipe is **unverified**.

The receiver only consumes selected ready PNGs. `ng/tools/build_catalog.py` runs
on the build host, using Pillow and (for SVG only) CairoSVG. Its inputs are:

- a privately captured profile and the corresponding original sample directory;
- an explicit mapping of calibration samples and desired logo IDs to
  `picons/picons` source paths, pinned to a full upstream Git SHA;
- a rendering recipe with canvas/inner dimensions;
- an output directory and a raw GitHub base URL under this repository.

```sh
python ng/tools/build_catalog.py --profile /private/profile.json \
  --originals /private/samples --mapping /private/mapping.json \
  --recipe /private/recipe.json --output /private/catalog \
  --base-url https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/COMMIT/ng/catalog
```

The builder fetches only explicit selected source logos and requires regenerated
calibration images to reproduce all original sample pixels. If calibration fails,
no public manifest is generated. Its report remains on the build host. Originals,
private receiver references and bouquet/provider data are not included in output.
A generated catalogue contains only logo IDs, PNG checksums/sizes, source
provenance and upstream GPL attribution. The receiver materializes destination
filenames locally. Conflicting IPTV target names are excluded.

The default receiver manifest location is `ng/catalog/manifest.json` on this
branch. That manifest intentionally does not exist until calibration and catalogue
hosting are complete: an unavailable or mismatched catalogue makes no changes.
Checksums establish integrity relative to the trusted GitHub repository; this is
not a separate cryptographic signing system.

## Recovery

Backups include verified preimages and a write-ahead `transaction.json`, written
and fsynced before any destination replacement. Each destination change uses an
atomic rename and directory fsync. The Backups screen can restore committed or
interrupted batches. Recovery rejects corrupt preimages, a different destination,
symlink targets or files changed by another application. New files are removed
when their batch is restored. Backups are retained rather than deleted silently.

Do not publish `ng/release.json` as stable or update the official root
`update.json` until the receiver/display/style gates in VALIDATION.md are passed.
No changes to IPToSatPro, EPGManager or bouquets are part of this plugin.
