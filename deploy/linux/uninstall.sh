#!/usr/bin/env bash
set -euo pipefail

remove_data=0
confirmed=0
install_root=""
skip_service=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --remove-data) remove_data=1; shift ;;
    --confirm-data-removal) confirmed=1; shift ;;
    --root) [[ $# -ge 2 ]] || { echo "--root requires a directory" >&2; exit 64; }; install_root="${2%/}"; shift 2 ;;
    --skip-service) skip_service=1; shift ;;
    --help|-h)
      echo "Usage: sudo ./uninstall-linux.sh [--remove-data --confirm-data-removal]"
      echo "Removes startup registration. All application, configuration and library files are retained."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 64 ;;
  esac
done
if [[ -n "${install_root}" ]]; then
  [[ "${install_root}" == /* && "${install_root}" != "/" ]] || { echo "--root must be a non-root absolute directory." >&2; exit 64; }
  [[ "${skip_service}" == "1" ]] || { echo "--root requires --skip-service." >&2; exit 64; }
fi
if [[ -z "${install_root}" && "${EUID}" -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 77
fi

opt_root="${install_root}/opt/blankbox"
config_root="${install_root}/etc/blankbox"
data_root="${install_root}/var/lib/blankbox"
unit_root="${install_root}/etc/systemd/system"
helper="${install_root}/usr/local/libexec/blankbox-local-name"

if [[ "${remove_data}" == "1" && "${confirmed}" != "1" ]]; then
  echo "Refusing data removal without --confirm-data-removal." >&2
  exit 64
fi

if [[ "${skip_service}" != "1" ]]; then
  systemctl disable --now blankbox.service 2>/dev/null || true
  systemctl disable --now blankbox-local-name.service 2>/dev/null || true
fi
# Keep application files: owners may have added files inside these directories.
# Remove service definitions only when they match an installed release template.
if [[ -L "${opt_root}/current" ]]; then
  release="$(readlink -f "${opt_root}/current")"
  case "${release}" in "${opt_root}"/releases/*)
    for name in blankbox blankbox-local-name; do
      template="${release}/deploy/linux/${name}.service"
      if [[ -f "${template}" ]] && cmp -s "${template}" "${unit_root}/${name}.service"; then
        rm -f "${unit_root}/${name}.service"
      fi
    done ;;
  esac
fi
if [[ "${skip_service}" != "1" ]]; then systemctl daemon-reload; fi

if [[ "${remove_data}" == "1" ]]; then
  echo "Data removal requested. For file safety, inspect and remove only the intended catalog/media files manually after verifying your backup."
  echo "Retained: ${config_root} and ${data_root}"
  echo "Startup registration was removed; all files were retained."
else
  echo "Blank Box startup was removed. Application, configuration, data, and other files were retained for reinstall or manual recovery."
  echo "Preserved: ${config_root} and ${data_root}"
fi
