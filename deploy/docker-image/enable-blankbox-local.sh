#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Advertise a friendly Blank Box address on the local network.

Usage: sudo ./enable-blankbox-local.sh [--port NUMBER] [--name NAME.local]
       ./enable-blankbox-local.sh --root DIRECTORY --skip-service

This publishes an mDNS address only on the local network. It does not expose
Blank Box to the internet and does not add HTTPS.
EOF
}

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_root=""
skip_service=0
local_name="blankbox.local"
local_port="25265"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) [[ $# -ge 2 ]] || { echo "--port requires a number" >&2; exit 64; }; local_port="$2"; shift 2 ;;
    --name) [[ $# -ge 2 ]] || { echo "--name requires a .local name" >&2; exit 64; }; local_name="${2,,}"; shift 2 ;;
    --root) [[ $# -ge 2 ]] || { echo "--root requires a directory" >&2; exit 64; }; install_root="${2%/}"; shift 2 ;;
    --skip-service) skip_service=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
  esac
done

[[ "${local_name}" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.local$ ]] || { echo "Use a name such as blankbox.local." >&2; exit 64; }
[[ "${local_port}" =~ ^[0-9]+$ ]] && (( local_port >= 1 && local_port <= 65535 )) || { echo "Use a port from 1 to 65535." >&2; exit 64; }
[[ -f "${package_dir}/blankbox-local-name.sh" && -f "${package_dir}/blankbox-local-name.service" ]] || { echo "Local discovery files are missing from this package." >&2; exit 66; }
if [[ -n "${install_root}" && "${skip_service}" != "1" ]]; then echo "--root requires --skip-service." >&2; exit 64; fi
if [[ -z "${install_root}" && "${EUID}" -ne 0 ]]; then echo "Run this command with sudo." >&2; exit 77; fi

if [[ "${skip_service}" != "1" ]]; then
  command -v systemctl >/dev/null || { echo "systemd is required." >&2; exit 69; }
  command -v avahi-publish >/dev/null || { echo "Install avahi-daemon and avahi-utils first." >&2; exit 69; }
  command -v ip >/dev/null || { echo "Install iproute2 first." >&2; exit 69; }
fi

install -d -m 0755 "${install_root}/usr/local/libexec" "${install_root}/etc/systemd/system" "${install_root}/etc/blankbox"
install -m 0755 "${package_dir}/blankbox-local-name.sh" "${install_root}/usr/local/libexec/blankbox-local-name"
install -m 0644 "${package_dir}/blankbox-local-name.service" "${install_root}/etc/systemd/system/blankbox-local-name.service"
printf 'BLANKBOX_LOCAL_NAME=%s\nBLANKBOX_LOCAL_PORT=%s\n' "${local_name}" "${local_port}" > "${install_root}/etc/blankbox/local-name.env"
chmod 0644 "${install_root}/etc/blankbox/local-name.env"

if [[ "${skip_service}" == "1" ]]; then
  echo "Blank Box local-name helper staged below ${install_root}."
  exit 0
fi

systemctl daemon-reload
systemctl enable --now avahi-daemon.service blankbox-local-name.service
echo "Local discovery enabled: http://${local_name}:${local_port}"
echo "This address works only on devices whose network supports mDNS."
