#!/bin/sh
set -eu

REPO_RAW="https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main"
MANIFEST_URL="$REPO_RAW/update.json"
WORK="/tmp/piconmanagerpro-online"
MANIFEST="$WORK/update.json"
B64="$WORK/package.b64"
IPK="$WORK/package.ipk"

say() { echo "[PiconManager Pro] $*"; }
fail() { echo "[PiconManager Pro] ERROR: $*" >&2; exit 1; }

fetch() {
    url="$1"; out="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$out" "$url" || return 1
    elif command -v curl >/dev/null 2>&1; then
        curl -fL --connect-timeout 30 -o "$out" "$url" || return 1
    else
        return 1
    fi
}

rm -rf "$WORK"
mkdir -p "$WORK"

say "Downloading release manifest..."
fetch "$MANIFEST_URL" "$MANIFEST" || fail "Cannot download update.json"

command -v python3 >/dev/null 2>&1 || fail "python3 is required on this OpenATV image"

VERSION="$(python3 - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])
PY
)"
PACKAGE="$(python3 - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["package"])
PY
)"
SHA256="$(python3 - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["sha256"])
PY
)"
PARTS="$(python3 - "$MANIFEST" <<'PY'
import json,sys
print(int(json.load(open(sys.argv[1], encoding="utf-8"))["parts"]))
PY
)"
PART_BASE="$(python3 - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["parts_base_url"])
PY
)"

say "Release: $VERSION"
say "Downloading package from GitHub in $PARTS parts..."
: > "$B64"
i=1
while [ "$i" -le "$PARTS" ]; do
    n="$(printf '%02d' "$i")"
    part="$WORK/part$n"
    fetch "$PART_BASE/part$n" "$part" || fail "Download failed: part$n"
    cat "$part" >> "$B64"
    i=$((i + 1))
done

say "Decoding IPK..."
if command -v base64 >/dev/null 2>&1; then
    base64 -d "$B64" > "$IPK" 2>/dev/null || fail "base64 decode failed"
else
    python3 - "$B64" "$IPK" <<'PY'
import base64,sys
data=open(sys.argv[1],"rb").read()
open(sys.argv[2],"wb").write(base64.b64decode(data))
PY
fi

ACTUAL="$(python3 - "$IPK" <<'PY'
import hashlib,sys
h=hashlib.sha256()
with open(sys.argv[1],"rb") as f:
    for b in iter(lambda:f.read(1024*1024), b""):
        h.update(b)
print(h.hexdigest())
PY
)"
[ "$ACTUAL" = "$SHA256" ] || fail "SHA-256 mismatch. Expected $SHA256, got $ACTUAL"
say "SHA-256 OK"

command -v opkg >/dev/null 2>&1 || fail "opkg not found"
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

if [ "${PICONMANAGERPRO_NO_RESTART:-0}" = "1" ]; then
    say "GUI restart skipped by PICONMANAGERPRO_NO_RESTART=1"
    exit 0
fi

say "Restarting Enigma2 GUI..."
init 4
sleep 2
init 3
