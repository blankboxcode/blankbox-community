#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${package_dir}"
[[ -f MANIFEST.sha256 && -f Dockerfile && -f compose.yaml ]] || { echo "Run this script from an extracted Blank Box package." >&2; exit 66; }
[[ -f VERSION ]] || { echo "VERSION is missing from this release package." >&2; exit 66; }
command -v docker >/dev/null || { echo "Docker with the Compose plugin is required." >&2; exit 69; }
docker compose version >/dev/null
if ! docker info >/dev/null; then
  echo "Cannot access Docker. If Docker commands on this host require sudo, run sudo ./upgrade-docker.sh from this folder. Keep your project and other Compose settings in .env when using sudo." >&2
  exit 77
fi
python3 release_files.py . --allow-configuration

release_hash="$(sha256sum MANIFEST.sha256 | awk '{print substr($1,1,12)}')"
release_version="$(tr -d '[:space:]' < VERSION)"
[[ "${release_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || { echo "VERSION is invalid." >&2; exit 65; }
candidate_image="blankbox-community:${release_version}-${release_hash}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
previous_image_tag="${BLANKBOX_PREVIOUS_IMAGE:-blankbox-community:previous-${timestamp}-${release_hash}}"
configured_image="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["blankbox"]["image"])')"
[[ "${configured_image}" != *@* ]] || { echo "Use a local image tag for managed upgrades, not a registry digest." >&2; exit 65; }
if ! container="$(docker compose ps --all -q blankbox)"; then
  echo "Could not read the existing Blank Box container. Check the Docker error above; no update was activated." >&2
  exit 69
fi
[[ -n "${container}" ]] || {
  echo "No existing Blank Box container was found. For an update, start the current release with its current user and storage settings first. For a new installation, use docker compose up." >&2
  exit 65
}

# Resolve the previous account without mounting or opening any library data.
# Numeric IDs are retained even when an image's default account changes.
image_identity() {
  local image="$1" selected_user="$2"
  local -a arguments=(docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges)
  [[ -z "${selected_user}" ]] || arguments+=(--user "${selected_user}")
  arguments+=(--entrypoint python3 "${image}" -c 'import os; uid,gid=os.getuid(),os.getgid(); assert uid > 0, "Blank Box must run as a non-root user"; print(f"{uid}:{gid}")')
  "${arguments[@]}"
}

previous_image="$(docker inspect --format '{{.Image}}' "${container}")"
previous_user="$(docker inspect --format '{{.Config.User}}' "${container}")"
if ! existing_user="$(image_identity "${previous_image}" "${previous_user}")"; then
  echo "Could not establish the existing non-root UID/GID. No update was activated." >&2
  exit 65
fi
IFS=: read -r retained_uid retained_gid <<< "${existing_user}"
if [[ "${BLANKBOX_UID+x}" == x && "${BLANKBOX_UID}" != "${retained_uid}" ]] || [[ "${BLANKBOX_GID+x}" == x && "${BLANKBOX_GID}" != "${retained_gid}" ]]; then
  echo "Your shell's BLANKBOX_UID/GID settings differ from the existing installation (${existing_user}). Keep its current IDs while updating; no update was activated." >&2
  exit 65
fi
BLANKBOX_UID="${retained_uid}"
BLANKBOX_GID="${retained_gid}"
export BLANKBOX_UID BLANKBOX_GID
configured_user="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["blankbox"].get("user", ""))')"
catalog_backup=""
has_previous=0
docker build --tag "${candidate_image}" --file Dockerfile .
if ! candidate_user="$(image_identity "${candidate_image}" "${configured_user}")" || [[ "${candidate_user}" != "${existing_user}" ]]; then
  echo "The configured UID/GID differs from the existing installation (${existing_user}). Keep the current user settings while updating; a user or storage move is a separate step. No update was activated." >&2
  exit 65
fi

# Persist the retained IDs so ordinary Compose recreation uses the same account.
# Replace only these two settings and keep credentials/configuration private.
python3 - <<'PY'
from pathlib import Path
import os
import re
import tempfile

path=Path('.env')
if path.is_symlink() or (path.exists() and not path.is_file()):
    raise SystemExit('The local .env must be a regular file; no update was activated.')
original=path.stat() if path.exists() else Path('.').stat()
text=path.read_text(encoding='utf-8') if path.exists() else ''
text=''.join(line for line in text.splitlines(keepends=True)
             if not re.match(r'^\s*(?:export\s+)?BLANKBOX_(?:UID|GID)\s*=',line))
if text and not text.endswith('\n'):
    text+='\n'
text+=f'BLANKBOX_UID={os.environ["BLANKBOX_UID"]}\nBLANKBOX_GID={os.environ["BLANKBOX_GID"]}\n'
temporary=None
try:
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir='.',prefix='.env.uid-',delete=False) as file:
        temporary=Path(file.name)
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    if os.geteuid()==0:
        os.chown(temporary,original.st_uid,original.st_gid)
    os.replace(temporary,path)
finally:
    if temporary is not None:
        temporary.unlink(missing_ok=True)
PY
echo "Keeping the existing Docker user ${existing_user}."
if [[ -n "${container}" ]]; then
  has_previous=1
  docker tag "${previous_image}" "${previous_image_tag}"
  docker compose stop blankbox
  if ! catalog_backup="$(BLANKBOX_IMAGE="${previous_image_tag}" docker compose run --rm --no-deps --entrypoint python3 blankbox /opt/blankbox/maintenance.py backup --destination "/data/upgrades/pre-docker-${timestamp}-${release_hash}.sqlite3")"; then
    BLANKBOX_IMAGE="${previous_image_tag}" docker compose up --detach --wait
    echo "Backup failed; prior container restarted." >&2; exit 74
  fi
fi

if BLANKBOX_IMAGE="${candidate_image}" docker compose up --detach --wait --wait-timeout 240; then
  # Advance the configured local tag only after acceptance. A later ordinary
  # compose up therefore keeps this accepted image; configuration stays intact.
  docker tag "${candidate_image}" "${configured_image}"
  echo "Blank Box Docker is ready on http://${BLANKBOX_BIND_ADDRESS:-127.0.0.1}:${BLANKBOX_PUBLISHED_PORT:-25265} using ${candidate_image}."
  [[ -z "${catalog_backup}" ]] || echo "Pre-upgrade catalog backup: ${catalog_backup}"
  [[ "${has_previous}" == "0" ]] || echo "Previous image retained as ${previous_image_tag}."
  exit 0
fi

echo "The candidate container did not become healthy." >&2
if [[ "${has_previous}" == "1" ]]; then
  docker compose stop blankbox || true
  if [[ -n "${catalog_backup}" ]]; then
    BLANKBOX_IMAGE="${candidate_image}" docker compose run --rm --no-deps --entrypoint python3 blankbox /opt/blankbox/maintenance.py restore --backup "${catalog_backup}"
  fi
  BLANKBOX_IMAGE="${previous_image_tag}" docker compose up --detach --wait --wait-timeout 240 || {
    echo "The previous container also failed to recover. Inspect docker compose logs immediately." >&2
    exit 70
  }
  echo "The previous Blank Box image and catalog were restored." >&2
fi
exit 70
