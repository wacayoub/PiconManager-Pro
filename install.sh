#!/bin/sh
set -eu

REPO_RAW="https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main"
MANIFEST_URL="$REPO_RAW/update.json"
WORK="/tmp/piconmanagerpro-online"
MANIFEST="$WORK/update.json"
IPK="$WORK/package.ipk"
B64="$WORK/package.b64"

say() { echo "[PiconManager Pro] $*"; }
fail() { echo "[PiconManager Pro] ERROR: $*" >&2; exit 1; }

fetch() {
    url="$1"
    out="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q -O "$out" "$url" || return 1
    elif command -v curl >/dev/null 2>&1; then
        curl -fL -o "$out" "$url" || return 1
    else
        return 1
    fi
}

json_get() {
    key="$1"
    python3 - "$MANIFEST" "$key" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
value = data.get(sys.argv[2], "")
if value is None:
    value = ""
print(value)
PY
}

rm -rf "$WORK"
mkdir -p "$WORK"

command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v opkg >/dev/null 2>&1 || fail "opkg not found"

say "Downloading release manifest..."
fetch "$MANIFEST_URL" "$MANIFEST" || fail "Cannot download update.json"

VERSION="$(json_get version)"
PACKAGE="$(json_get package)"
URL="$(json_get url)"
SHA256="$(json_get sha256)"
EXPECTED_SIZE="$(json_get size)"

[ -n "$VERSION" ] || fail "Manifest has no version"
[ -n "$PACKAGE" ] || fail "Manifest has no package"
[ -n "$SHA256" ] || fail "Manifest has no SHA-256"

say "Release: $VERSION"

if [ -n "$URL" ]; then
    say "Downloading $PACKAGE from GitHub..."
    if ! fetch "$URL" "$IPK"; then
        say "Direct download failed; trying fallback package parts..."
        URL=""
    fi
fi

if [ -z "$URL" ]; then
    PARTS="$(json_get parts)"
    PART_BASE="$(json_get parts_base_url)"
    [ -n "$PARTS" ] || fail "No direct URL and no fallback parts"
    [ -n "$PART_BASE" ] || fail "No fallback parts URL"

    say "Downloading fallback package in $PARTS parts..."
    : > "$B64"
    i=1
    while [ "$i" -le "$PARTS" ]; do
        n="$(printf '%02d' "$i")"
        part="$WORK/part$n"
        fetch "$PART_BASE/part$n" "$part" || fail "Download failed: part$n"
        cat "$part" >> "$B64"
        i=$((i + 1))
    done

    say "Decoding fallback package..."
    if command -v base64 >/dev/null 2>&1; then
        base64 -d "$B64" > "$IPK" 2>/dev/null || fail "base64 decode failed"
    else
        python3 - "$B64" "$IPK" <<'PY'
import base64, sys
with open(sys.argv[1], "rb") as src:
    data = src.read()
with open(sys.argv[2], "wb") as dst:
    dst.write(base64.b64decode(data))
PY
    fi
fi

ACTUAL_SIZE="$(wc -c < "$IPK" | tr -d ' ')"
if [ -n "$EXPECTED_SIZE" ] && [ "$ACTUAL_SIZE" != "$EXPECTED_SIZE" ]; then
    fail "Package size mismatch. Expected $EXPECTED_SIZE, got $ACTUAL_SIZE"
fi

ACTUAL_SHA="$(python3 - "$IPK" <<'PY'
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        h.update(block)
print(h.hexdigest())
PY
)"

[ "$ACTUAL_SHA" = "$SHA256" ] || fail "SHA-256 mismatch. Expected $SHA256, got $ACTUAL_SHA"
say "Integrity check: OK"

PKGNAME="enigma2-plugin-extensions-piconmanagerpro"
if opkg list-installed 2>/dev/null | grep -q "^$PKGNAME "; then
    say "Updating/reinstalling $PKGNAME..."
    opkg install --force-reinstall --force-overwrite "$IPK"
else
    say "Installing $PKGNAME..."
    opkg install --force-overwrite "$IPK"
fi

rm -rf "$WORK"
say "PiconManager Pro $VERSION installed successfully."

if command -v piconmanagerpro-check >/dev/null 2>&1; then
    piconmanagerpro-check || true
fi

if [ "${PICONMANAGERPRO_NO_RESTART:-0}" = "1" ]; then
    say "GUI restart skipped."
    exit 0
fi

say "Restarting Enigma2 GUI..."
init 4
sleep 2
init 3
