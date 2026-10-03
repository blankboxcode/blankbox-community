#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
installer="${package_dir}/install-linux.sh"
uninstaller="${package_dir}/uninstall-linux.sh"
[[ -x "${installer}" && -x "${uninstaller}" ]] || { echo "Run setup-linux.sh from an extracted Blank Box release." >&2; exit 66; }
[[ "${EUID}" -eq 0 ]] || { echo "Run: sudo ./setup-linux.sh" >&2; exit 77; }
temporary=""
cleanup() { [[ -z "${temporary}" ]] || rm -f "${temporary}"; }
trap cleanup EXIT

ask_port() {
  local value
  read -r -p "Web port [25265]: " value
  value="${value:-25265}"
  [[ "${value}" =~ ^[0-9]+$ ]] && (( value >= 1024 && value <= 65535 )) || { echo "Use a port from 1024 to 65535." >&2; return 1; }
  printf '%s' "${value}"
}

install_blankbox() {
  echo
  echo "Where will you open Blank Box?"
  echo "  1) On this computer (direct access)"
  echo "  2) On my trusted home network (using this server's IP address)"
  echo "  3) The same home-network access, plus the name blankbox.local"
  echo "Options 2 and 3 also work on this computer. The name in option 3 is optional."
  echo "None of these choices sets up access from outside your home or turns off outgoing Internet access."
  echo "A private proxy or VPN you already configured has its own access settings."
  read -r -p "Choose [1-3]: " access
  [[ "${access}" =~ ^[123]$ ]] || { echo "Choose 1, 2, or 3." >&2; return 1; }
  port="$(ask_port)" || return 1
  echo
  read -r -p "Allow Blank Box to read a connected audio-CD drive? No extra CD software is required. [Y/n]: " audio_cd_answer
  case "${audio_cd_answer}" in
    y|Y|yes|YES|'') ;;
    n|N|no|NO) audio_cd_answer=no ;;
    *) echo "Choose y or n for optical-drive access." >&2; return 1 ;;
  esac

  temporary="$(mktemp)"
  host="127.0.0.1"; [[ "${access}" == "1" ]] || host="0.0.0.0"
  python3 -c 'import json,sys; print(json.dumps({"data":"/var/lib/blankbox","sources":[],"backup":None,"host":sys.argv[1],"port":int(sys.argv[2]),"backupEveryHours":None},indent=2))' "${host}" "${port}" > "${temporary}"

  args=(--config "${temporary}")
  [[ "${access}" == "1" ]] || args+=(--lan-access)
  [[ "${access}" != "3" ]] || args+=(--enable-local-name)
  [[ "${audio_cd_answer}" != "no" ]] || args+=(--no-audio-cd)
  "${installer}" "${args[@]}"

  # The low-level installer preserves existing configuration. The wizard is an
  # explicit request to update only listener choices while retaining data,
  # sources, backup settings, and every other existing value.
  python3 -c 'import json,os,sys,tempfile; path=sys.argv[1]; value=json.load(open(path,encoding="utf-8")); value["host"]=sys.argv[2]; value["port"]=int(sys.argv[3]); fd,pending=tempfile.mkstemp(prefix=".config.",suffix=".json",dir=os.path.dirname(path)); os.close(fd); open(pending,"w",encoding="utf-8").write(json.dumps(value,indent=2)+"\n"); os.replace(pending,path)' /etc/blankbox/config.json "${host}" "${port}"
  chown root:blankbox /etc/blankbox/config.json
  chmod 0640 /etc/blankbox/config.json
  systemctl restart blankbox.service
  if [[ "${access}" == "3" ]]; then "${package_dir}/enable-blankbox-local.sh" --port "${port}"; fi
  if [[ "${access}" != "3" ]]; then systemctl disable --now blankbox-local-name.service 2>/dev/null || true; fi
  rm -f "${temporary}"
  temporary=""

  echo
  echo "On this computer, open http://127.0.0.1:${port}"
  [[ "${access}" == "1" ]] || echo "On another home-network device, open http://SERVER-IP:${port} (replace SERVER-IP with this server's local IP address)."
  [[ "${access}" != "3" ]] || echo "You can also use http://blankbox.local:${port} where local discovery works; use the IP address if the name does not work."
  echo "Access key: /var/lib/blankbox/access-key.txt"
}

echo "Blank Box Community setup"
echo "  1) Install or update Blank Box"
echo "  2) Uninstall Blank Box"
echo "  3) Exit"
read -r -p "Choose [1-3]: " action
case "${action}" in
  1) install_blankbox ;;
  2) "${uninstaller}" ;;
  3) exit 0 ;;
  *) echo "Choose 1, 2, or 3." >&2; exit 64 ;;
esac
