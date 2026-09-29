#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Roll back the most recent successful Blank Box native Linux upgrade.

Usage: sudo /opt/blankbox/current/rollback-linux.sh
       sudo /opt/blankbox/current/rollback-linux.sh --restore-pre-upgrade-catalog
       ./rollback-linux.sh --root DIRECTORY --skip-service

By default, rollback preserves the current catalog and proceeds only when the
previous Core can read it. The restore flag is required if a newer schema means
the pre-upgrade catalog must be restored; that intentionally discards catalog
changes made after the upgrade. An emergency copy of the current catalog is
created before either rollback path.
EOF
}

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_root=""
skip_service=0
restore_pre_upgrade=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) [[ $# -ge 2 ]] || { echo "--root requires a directory" >&2; exit 64; }; install_root="${2%/}"; shift 2 ;;
    --skip-service) skip_service=1; shift ;;
    --restore-pre-upgrade-catalog) restore_pre_upgrade=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
  esac
done

if [[ -n "${install_root}" && "${skip_service}" != "1" ]]; then echo "--root requires --skip-service." >&2; exit 64; fi
if [[ -z "${install_root}" && "${EUID}" -ne 0 ]]; then echo "Run rollback with sudo." >&2; exit 77; fi
opt_root="${install_root}/opt/blankbox"
config_file="${install_root}/etc/blankbox/config.json"
current_link="${opt_root}/current"
[[ -L "${current_link}" && -f "${config_file}" ]] || { echo "Blank Box native installation was not found." >&2; exit 66; }
current_release="$(readlink -f "${current_link}")"
maintenance="${current_release}/maintenance.py"
[[ -f "${maintenance}" ]] || { echo "This release does not contain lifecycle support." >&2; exit 69; }

run_core_tool() {
  if [[ "${skip_service}" == "1" ]]; then python3 "$@"; else runuser -u blankbox -- python3 "$@"; fi
}
switch_release() {
  local target="$1" pending="${opt_root}/.rollback-current-$$"
  [[ ! -e "${pending}" ]] || { echo "Temporary rollback link already exists: ${pending}" >&2; return 1; }
  ln -s "${target}" "${pending}"
  mv -Tf "${pending}" "${current_link}"
}
health_url="$(python3 -c 'import json,sys; value=json.load(open(sys.argv[1],encoding="utf-8")); host=value.get("host","127.0.0.1"); host="127.0.0.1" if host=="0.0.0.0" else "::1" if host=="::" else host; host=f"[{host}]" if ":" in host and not host.startswith("[") else host; print("http://{}:{}/health/ready".format(host,int(value.get("port",25265))))' "${config_file}")"
wait_until_ready() {
  for _ in {1..30}; do
    if python3 -c 'import sys,urllib.request; urllib.request.urlopen(sys.argv[1],timeout=1)' "${health_url}" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

status="$(run_core_tool "${maintenance}" state-field --config "${config_file}" --field status)"
previous_release="$(run_core_tool "${maintenance}" state-field --config "${config_file}" --field previousRelease)"
activated_release="$(run_core_tool "${maintenance}" state-field --config "${config_file}" --field currentRelease)"
pre_upgrade_backup="$(run_core_tool "${maintenance}" state-field --config "${config_file}" --field catalogBackup)"
[[ "${status}" == "active" || "${status}" == "pending" ]] || { echo "The latest upgrade is not in an active rollback state." >&2; exit 65; }
[[ "${activated_release}" == "${current_release}" ]] || { echo "Installed release and upgrade state do not match; refusing rollback." >&2; exit 65; }
case "${previous_release}" in "${opt_root}"/releases/*) ;; *) echo "Previous release is outside the managed release directory." >&2; exit 65 ;; esac
[[ -d "${previous_release}" && -f "${previous_release}/doctor.py" ]] || { echo "Previous release is unavailable." >&2; exit 66; }

if [[ "${skip_service}" != "1" ]]; then systemctl stop blankbox.service; fi
runtime_data="$(python3 "${maintenance}" data-path --config "${config_file}")"
if ! emergency_backup="$(run_core_tool "${maintenance}" backup --config "${config_file}" --destination "${runtime_data}/upgrades/pre-rollback-$(date -u +%Y%m%dT%H%M%SZ)-$$-$(basename "${current_release}").sqlite3")"; then
  if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
  echo "Emergency catalog backup failed. No rollback switch was made." >&2
  exit 74
fi

catalog_restored=0
if ! run_core_tool "${previous_release}/doctor.py" --config "${config_file}" >/dev/null; then
  if [[ "${restore_pre_upgrade}" != "1" ]]; then
    if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
    echo "The previous Core cannot read the current catalog. No switch was made. Re-run with --restore-pre-upgrade-catalog only if you accept losing post-upgrade catalog changes." >&2
    exit 65
  fi
  [[ -n "${pre_upgrade_backup}" && -f "${pre_upgrade_backup}" ]] || {
    if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
    echo "The verified pre-upgrade catalog backup is unavailable. No switch was made." >&2
    exit 66
  }
  run_core_tool "${maintenance}" restore --config "${config_file}" --backup "${pre_upgrade_backup}" >/dev/null
  catalog_restored=1
  if ! run_core_tool "${previous_release}/doctor.py" --config "${config_file}" >/dev/null; then
    if [[ -n "${emergency_backup}" ]]; then run_core_tool "${maintenance}" restore --config "${config_file}" --backup "${emergency_backup}" >/dev/null; fi
    if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
    echo "The previous release still failed diagnostics after catalog restoration. No code switch was made." >&2
    exit 65
  fi
fi

if ! switch_release "${previous_release}"; then
  if [[ "${catalog_restored}" == "1" && -n "${emergency_backup}" ]]; then run_core_tool "${maintenance}" restore --config "${config_file}" --backup "${emergency_backup}" >/dev/null; fi
  if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
  echo "Rollback release switch failed. The newer release remains selected." >&2
  exit 73
fi
unit_dir="${install_root}/etc/systemd/system"
install -m 0644 "${previous_release}/deploy/linux/blankbox.service" "${unit_dir}/blankbox.service"
if [[ "${skip_service}" == "1" ]]; then
  run_core_tool "${previous_release}/doctor.py" --config "${config_file}" >/dev/null
else
  systemctl daemon-reload
  systemctl start blankbox.service
  if ! wait_until_ready; then
    echo "Rollback did not become ready. Restoring the newer release and emergency catalog." >&2
    systemctl stop blankbox.service || true
    switch_release "${current_release}"
    if [[ -n "${emergency_backup}" ]]; then run_core_tool "${maintenance}" restore --config "${config_file}" --backup "${emergency_backup}" >/dev/null; fi
    install -m 0644 "${current_release}/deploy/linux/blankbox.service" "${unit_dir}/blankbox.service"
    systemctl daemon-reload
    systemctl start blankbox.service
    wait_until_ready || { echo "Recovery failed. Inspect systemctl status blankbox immediately." >&2; exit 70; }
    exit 70
  fi
fi

state_args=(write-state --config "${config_file}" --previous "${current_release}" --current "${previous_release}" --status rolled-back)
if [[ -n "${emergency_backup}" ]]; then state_args+=(--backup "${emergency_backup}"); fi
run_core_tool "${maintenance}" "${state_args[@]}" >/dev/null
if [[ "${catalog_restored}" == "1" ]]; then
  echo "Blank Box rolled back to $(basename "${previous_release}") with the verified pre-upgrade catalog. The emergency newer-catalog backup is ${emergency_backup}."
else
  echo "Blank Box rolled back to $(basename "${previous_release}"). Current catalog data was preserved."
fi
