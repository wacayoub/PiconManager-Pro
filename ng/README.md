# PiconManager NG 2027

Development branch: **2.0.0-dev1** (NOT an installable release).

Target: Vu+ Zero 4K, OpenATV 8.0.1, Python 3.

Sources of inspiration:
- Chocholousek Picons — familiar UI/workflow and **exact existing user's visual style**, subject to an original sample.
- picons/picons — current channel-logo and service-reference catalogue (independent GPLv3 project).
- Existing PiconManager Pro v1.5.1 — preserve useful functionality and GitHub update infrastructure, including LyngSat.

## First implemented scope
- Enigma2 bouquet scanner, duplicate filtering and full SRP identifiers.
- Safe inventory of installed/missing picons.
- Strict, versioned visual-style manifests.
- Staged checksum-verified PNG replacement, mandatory backup and transaction recovery.
- Read-only experimental Enigma2 menu.
- Offline unit tests, 5 passed.

## Pending before replacing production v1.5.1
- Inspect a sample of the actual installed Chocholousek style.
- Render matched replacements in that EXACT style. Do not substitute a visually different upstream pack.
- Prepare selective hosted catalogue using picons/picons; source generation should be off-receiver.
- Preview/confirmation UI, automatic scheduled updates with safeguards.
- Receiver-side hardware checks and secure package build.
- Check upstream art licences. Never modify bouquets, IPToSatPro or EPGManager.

**No receiver installation, package update, old release deletion or GitHub main change has occurred.**
