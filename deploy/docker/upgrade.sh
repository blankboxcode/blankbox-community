#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${package_dir}"
[[ -f MANIFEST.sha256 && -f Dockerfile && -f compose.yaml ]] || { echo "Run this script from an extracted Blank Box package." >&2; exit 66; }
[[ -f VERSION ]] || { echo "VERSION is missing from this release package." >&2; exit 66; }
command -v docker >/dev/null || { echo "Docker with the Compose plugin is required." >&2; exit 69; }
docker compose version >/dev/null
python3 release_files.py . --allow-configuration

release_hash="$(sha256sum MANIFEST.sha256 | awk '{print substr($1,1,12)}')"
release_version="$(tr -d '[:space:]' < VERSION)"
[[ "${release_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || { echo "VERSION is invalid." >&2; exit 65; }
candidate_image="blankbox-community:${release_version}-${release_hash}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
previous_image_tag="${BLANKBOX_PREVIOUS_IMAGE:-blankbox-community:previous-${timestamp}-${release_hash}}"
configured_image="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["blankbox"]["image"])')"
[[ "${configured_image}" != *@* ]] || { echo "Use a local image tag for managed upgrades, not a registry digest." >&2; exit 65; }
container="$(docker compose ps -q blankbox 2>/dev/null || true)"
catalog_backup=""
has_previous=0
docker build --tag "${candidate_image}" --file Dockerfile .
if [[ -n "${container}" ]]; then
  has_previous=1
  previous_image="$(docker inspect --format '{{.Image}}' "${container}")"
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
