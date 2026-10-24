# PiconManager NG 2.x

Branch: `dev/piconmanager-ng-v2`. Target: Vu+ Zero 4K, OpenATV 8.0.1 / Python 3.
Version: 2.0.0-r0, prepared for hardware validation. Official 1.5.1 is preserved.
See [VALIDATION.md](VALIDATION.md) for measured results and remaining release gates.

## Implemented

- Neo Dark dashboard and paginated channel/installed/missing views, native focus,
  remote navigation and color keys, separate HD and FHD geometries.
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
