#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

usage() {
  cat <<'EOF'
Install Blank Box Core as a native systemd service.

Usage: sudo ./install-linux.sh [--config FILE]
       ./install-linux.sh --root DIRECTORY --skip-service [--config FILE]

Options:
  --config FILE   Install this JSON configuration on a new installation.
                  An existing /etc/blankbox/config.json is always preserved.
  --root DIR      Stage files below DIR for a non-root installer test.
  --skip-service  Do not create a user or invoke systemctl (required with --root).
  --lan-access    Listen on the trusted LAN instead of this computer only.
  --enable-local-name
                  Enable LAN access and advertise blankbox.local through Avahi.
  --no-audio-cd   Do not grant the service account optical-drive access.
  --help          Show this help.

The installer never deletes or replaces the Blank Box data directory.
EOF
}

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_root=""
provided_config=""
skip_service=0
lan_access=0
enable_local_name=0
audio_cd_import=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) [[ $# -ge 2 ]] || { echo "--config requires a file" >&2; exit 64; }; provided_config="$2"; shift 2 ;;
    --root) [[ $# -ge 2 ]] || { echo "--root requires a directory" >&2; exit 64; }; install_root="${2%/}"; shift 2 ;;
    --skip-service) skip_service=1; shift ;;
    --lan-access) lan_access=1; shift ;;
    --enable-local-name) lan_access=1; enable_local_name=1; shift ;;
    --no-audio-cd) audio_cd_import=0; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
  esac
done

[[ -f "${package_dir}/server.py" && -f "${package_dir}/doctor.py" && -f "${package_dir}/maintenance.py" && -f "${package_dir}/MANIFEST.sha256" && -f "${package_dir}/VERSION" ]] || {
  echo "Run this installer from an extracted Blank Box release package." >&2
  exit 66
}
[[ -f "${package_dir}/deploy/linux/blankbox.service" ]] || { echo "The systemd service template is missing." >&2; exit 66; }
if [[ -n "${install_root}" && "${skip_service}" != "1" ]]; then
  echo "--root requires --skip-service." >&2
  exit 64
fi
if [[ -z "${install_root}" && "${EUID}" -ne 0 ]]; then
  echo "Run the system installation with sudo, or use --root DIR --skip-service to test it." >&2
  exit 77
fi
if [[ "${enable_local_name}" == "1" && "${skip_service}" == "1" ]]; then
  echo "--enable-local-name cannot be used with --skip-service." >&2
  exit 64
fi
command -v python3 >/dev/null || { echo "Python 3.10 or newer is required." >&2; exit 69; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || { echo "Python 3.10 or newer is required." >&2; exit 69; }
command -v sha256sum >/dev/null || { echo "sha256sum is required." >&2; exit 69; }
if [[ "${enable_local_name}" == "1" ]]; then
  command -v avahi-publish >/dev/null || { echo "Install avahi-daemon and avahi-utils before using --enable-local-name." >&2; exit 69; }
  command -v ip >/dev/null || { echo "Install iproute2 before using --enable-local-name." >&2; exit 69; }
fi
python3 "${package_dir}/release_files.py" "${package_dir}"
release_hash="$(sha256sum "${package_dir}/MANIFEST.sha256" | awk '{print substr($1,1,12)}')"
release_version="$(tr -d '[:space:]' < "${package_dir}/VERSION")"
[[ "${release_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || { echo "VERSION is invalid." >&2; exit 65; }

release_id="${release_version}-${release_hash}"
opt_root="${install_root}/opt/blankbox"
release_dir="${opt_root}/releases/${release_id}"
config_dir="${install_root}/etc/blankbox"
config_file="${config_dir}/config.json"
data_dir="${install_root}/var/lib/blankbox"
unit_dir="${install_root}/etc/systemd/system"

python3 -c 'import sys; sys.path.insert(0,sys.argv[1]); from file_safety import reject_links; [reject_links(p) for p in sys.argv[2:]]' "${package_dir}" "${opt_root}/releases" "${config_file}" "${data_dir}" "${unit_dir}/blankbox.service"
if [[ -e "${opt_root}" && ! -L "${opt_root}/current" && -n "$(ls -A "${opt_root}" 2>/dev/null)" ]]; then
  echo "Existing installation directory has no managed release pointer; preserve it and choose a clean destination." >&2; exit 73
fi
if [[ -e "${unit_dir}/blankbox.service" ]]; then
  previous_unit="${opt_root}/current/deploy/linux/blankbox.service"
  if [[ ! -L "${opt_root}/current" || ! -f "${previous_unit}" ]] || ! cmp -s "${previous_unit}" "${unit_dir}/blankbox.service"; then
    echo "An existing or customized service file was preserved. Save it separately before deliberately replacing it." >&2; exit 73
  fi
fi
if [[ "${skip_service}" != "1" ]]; then
  command -v systemctl >/dev/null || { echo "systemd is required for the native installer." >&2; exit 69; }
  command -v runuser >/dev/null || { echo "runuser is required for the native installer." >&2; exit 69; }
  if ! getent group blankbox >/dev/null; then groupadd --system blankbox; fi
  if ! id blankbox >/dev/null 2>&1; then useradd --system --gid blankbox --home-dir /var/lib/blankbox --shell /usr/sbin/nologin blankbox; fi
  if [[ "${audio_cd_import}" == "1" ]]; then
    if getent group cdrom >/dev/null; then usermod -aG cdrom blankbox
    elif getent group optical >/dev/null; then usermod -aG optical blankbox
    else echo "No optical-drive access group was found. Disc Import may need a device-specific permission rule." >&2
    fi
  fi
  install -d -m 0755 "${opt_root}/releases" "${config_dir}" "${unit_dir}"
  install -d -o blankbox -g blankbox -m 0700 "${data_dir}"
else
  install -d -m 0755 "${opt_root}/releases" "${config_dir}" "${unit_dir}"
  install -d -m 0700 "${data_dir}"
fi

if [[ ! -d "${release_dir}" ]]; then
  staging="${opt_root}/releases/.${release_id}.installing"
  [[ ! -e "${staging}" ]] || { echo "Incomplete staging path already exists: ${staging}" >&2; exit 73; }
  install -d -m 0755 "${staging}"
  cp -a "${package_dir}/." "${staging}/"
  # Extracting under a private umask must not leave root-owned public code or
  # bundled reference files unreadable by the service account.
  chmod -R a+rX,go-w "${staging}"
  python3 "${staging}/release_files.py" "${staging}"
  mv "${staging}" "${release_dir}"
fi

python3 "${release_dir}/release_files.py" "${release_dir}"

if [[ ! -f "${config_file}" ]]; then
  if [[ -n "${provided_config}" ]]; then
    [[ -f "${provided_config}" ]] || { echo "Configuration does not exist: ${provided_config}" >&2; exit 66; }
    python3 "${release_dir}/doctor.py" --config "${provided_config}" --json >/dev/null || { echo "Configuration diagnostics failed." >&2; exit 78; }
    install -m 0640 "${provided_config}" "${config_file}"
  else
    install -m 0640 "${release_dir}/deploy/config.example.json" "${config_file}"
  fi
  if [[ "${skip_service}" != "1" ]]; then chown root:blankbox "${config_file}"; fi
else
  echo "Preserving existing configuration: ${config_file}"
fi

if [[ "${lan_access}" == "1" ]]; then
  python3 -c 'import json,os,sys,tempfile; path=sys.argv[1]; value=json.load(open(path,encoding="utf-8")); value["host"]="0.0.0.0"; directory=os.path.dirname(path); fd,pending=tempfile.mkstemp(prefix=".config.",suffix=".json",dir=directory); os.close(fd); open(pending,"w",encoding="utf-8").write(json.dumps(value,indent=2)+"\n"); os.replace(pending,path)' "${config_file}"
  chmod 0640 "${config_file}"
  if [[ "${skip_service}" != "1" ]]; then chown root:blankbox "${config_file}"; fi
fi

run_core_tool() {
  if [[ "${skip_service}" == "1" ]]; then python3 "$@"; else runuser -u blankbox -- python3 "$@"; fi
}

switch_release() {
  local target="$1" pending="${opt_root}/.current-${release_hash}-$$"
  [[ ! -e "${pending}" ]] || { echo "Temporary release link already exists: ${pending}" >&2; return 1; }
  ln -s "${target}" "${pending}"
  mv -Tf "${pending}" "${opt_root}/current"
}

health_url="$(python3 -c 'import json,sys; value=json.load(open(sys.argv[1],encoding="utf-8")); host=value.get("host","127.0.0.1"); host="127.0.0.1" if host=="0.0.0.0" else "::1" if host=="::" else host; host=f"[{host}]" if ":" in host and not host.startswith("[") else host; print("http://{}:{}/health/ready".format(host,int(value.get("port",25265))))' "${config_file}")"
wait_until_ready() {
  local attempts=30
  if [[ -f "${opt_root}/current/bundled-metadata/catalog.json" ]] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1],encoding="utf-8")).get("packs") else 1)' "${opt_root}/current/bundled-metadata/catalog.json"; then attempts=180; fi
  for ((attempt=0;attempt<attempts;attempt++)); do
    if python3 -c 'import sys,urllib.request; urllib.request.urlopen(sys.argv[1],timeout=1)' "${health_url}" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

if [[ -e "${opt_root}/current" && ! -L "${opt_root}/current" ]]; then
  echo "Refusing to replace non-symlink path: ${opt_root}/current" >&2
  exit 73
fi
previous_release=""
if [[ -L "${opt_root}/current" ]]; then
  previous_release="$(readlink -f "${opt_root}/current")"
  [[ -d "${previous_release}" ]] || { echo "The current release link is broken." >&2; exit 73; }
fi

runtime_data="$(python3 "${release_dir}/maintenance.py" data-path --config "${config_file}")"
if [[ ! -d "${runtime_data}" ]]; then
  if [[ "${skip_service}" == "1" ]]; then install -d -m 0700 "${runtime_data}"; else install -d -o blankbox -g blankbox -m 0700 "${runtime_data}"; fi
fi
run_core_tool "${release_dir}/doctor.py" --config "${config_file}"
install -m 0644 "${release_dir}/deploy/linux/blankbox.service" "${unit_dir}/blankbox.service"

if [[ -n "${previous_release}" && "${previous_release}" != "${release_dir}" ]]; then
  if [[ "${skip_service}" != "1" ]]; then systemctl stop blankbox.service; fi
  upgrade_dir="${runtime_data}/upgrades"
  backup_name="pre-$(date -u +%Y%m%dT%H%M%SZ)-$(basename "${previous_release}")-to-${release_id}.sqlite3"
  if ! catalog_backup="$(run_core_tool "${release_dir}/maintenance.py" backup --config "${config_file}" --destination "${upgrade_dir}/${backup_name}")"; then
    if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
    echo "Pre-upgrade catalog backup failed. The prior release remains active." >&2
    exit 74
  fi
  pending_args=(write-state --config "${config_file}" --previous "${previous_release}" --current "${release_dir}" --status pending)
  if [[ -n "${catalog_backup}" ]]; then pending_args+=(--backup "${catalog_backup}"); fi
  run_core_tool "${release_dir}/maintenance.py" "${pending_args[@]}" >/dev/null
  if ! switch_release "${release_dir}"; then
    if [[ "${skip_service}" != "1" ]]; then systemctl start blankbox.service; fi
    echo "Release activation failed. The prior release remains selected." >&2
    exit 73
  fi
  if [[ "${skip_service}" == "1" ]]; then
    run_core_tool "${release_dir}/doctor.py" --config "${config_file}"
  else
    systemctl daemon-reload
    if ! systemctl start blankbox.service || ! wait_until_ready; then
      echo "The new release did not become ready. Restoring the prior release and catalog." >&2
      systemctl stop blankbox.service || true
      switch_release "${previous_release}"
      if [[ -n "${catalog_backup}" ]]; then run_core_tool "${release_dir}/maintenance.py" restore --config "${config_file}" --backup "${catalog_backup}"; fi
      install -m 0644 "${previous_release}/deploy/linux/blankbox.service" "${unit_dir}/blankbox.service"
      systemctl daemon-reload
      systemctl start blankbox.service
      wait_until_ready || { echo "Automatic recovery also failed. Inspect systemctl status blankbox immediately." >&2; exit 70; }
      exit 70
    fi
  fi
  state_args=(write-state --config "${config_file}" --previous "${previous_release}" --current "${release_dir}")
  if [[ -n "${catalog_backup}" ]]; then state_args+=(--backup "${catalog_backup}"); fi
  if ! run_core_tool "${release_dir}/maintenance.py" "${state_args[@]}" >/dev/null; then
    echo "Upgrade state could not be recorded. Restoring the prior release and catalog." >&2
    if [[ "${skip_service}" != "1" ]]; then systemctl stop blankbox.service || true; fi
    switch_release "${previous_release}"
    if [[ -n "${catalog_backup}" ]]; then run_core_tool "${release_dir}/maintenance.py" restore --config "${config_file}" --backup "${catalog_backup}"; fi
    install -m 0644 "${previous_release}/deploy/linux/blankbox.service" "${unit_dir}/blankbox.service"
    if [[ "${skip_service}" != "1" ]]; then
      systemctl daemon-reload
      systemctl start blankbox.service
      wait_until_ready || { echo "Automatic recovery also failed. Inspect systemctl status blankbox immediately." >&2; exit 70; }
    fi
    exit 70
  fi
  echo "Blank Box upgraded from $(basename "${previous_release}") to ${release_id}."
elif [[ -z "${previous_release}" ]]; then
  switch_release "${release_dir}"
fi

if [[ "${skip_service}" != "1" ]]; then
  systemctl daemon-reload
  systemctl enable --now blankbox.service
  wait_until_ready || { echo "Blank Box was installed but did not become ready. Run: systemctl status blankbox" >&2; exit 70; }
  if [[ "${enable_local_name}" == "1" ]]; then
    local_port="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1],encoding="utf-8")).get("port",25265)))' "${config_file}")"
    "${release_dir}/deploy/linux/enable-local-name.sh" --port "${local_port}"
  fi
  echo "Blank Box is installed and ready at ${health_url%/health/ready}"
  if [[ "${enable_local_name}" == "1" ]]; then echo "Friendly local address: http://blankbox.local:${local_port}"; fi
  echo "Access key: ${runtime_data}/access-key.txt"
  exit 0
fi

echo "Blank Box installer staging passed: ${release_dir}"
