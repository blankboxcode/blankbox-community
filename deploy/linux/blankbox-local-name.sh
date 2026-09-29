#!/usr/bin/env bash
set -euo pipefail

local_name="${BLANKBOX_LOCAL_NAME:-blankbox.local}"
local_port="${BLANKBOX_LOCAL_PORT:-25265}"
[[ "${local_name}" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.local$ ]] || { echo "Invalid .local name: ${local_name}" >&2; exit 64; }
[[ "${local_port}" =~ ^[0-9]+$ ]] && (( local_port >= 1 && local_port <= 65535 )) || { echo "Invalid local port: ${local_port}" >&2; exit 64; }
command -v ip >/dev/null || { echo "iproute2 is required for Blank Box local discovery." >&2; exit 69; }
command -v avahi-publish >/dev/null || { echo "avahi-utils is required for Blank Box local discovery." >&2; exit 69; }

address_pid=""
service_pid=""
cleanup() {
  [[ -z "${service_pid}" ]] || kill "${service_pid}" 2>/dev/null || true
  [[ -z "${address_pid}" ]] || kill "${address_pid}" 2>/dev/null || true
  [[ -z "${service_pid}" ]] || wait "${service_pid}" 2>/dev/null || true
  [[ -z "${address_pid}" ]] || wait "${address_pid}" 2>/dev/null || true
}
trap 'cleanup; exit 0' INT TERM

primary_ipv4() {
  ip -4 route get 224.0.0.251 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}'
}

while true; do
  address="$(primary_ipv4)"
  if [[ -z "${address}" ]]; then sleep 3; continue; fi

  avahi-publish -a -R "${local_name}" "${address}" &
  address_pid=$!
  sleep 1
  if ! kill -0 "${address_pid}" 2>/dev/null; then
    wait "${address_pid}" || true
    echo "Could not publish ${local_name}; another device may already be using it." >&2
    exit 73
  fi

  avahi-publish -s -H "${local_name}" "Blank Box" _http._tcp "${local_port}" "path=/" &
  service_pid=$!
  sleep 1
  if ! kill -0 "${service_pid}" 2>/dev/null; then
    cleanup
    echo "Could not advertise the Blank Box Web service." >&2
    exit 73
  fi

  while kill -0 "${address_pid}" 2>/dev/null && kill -0 "${service_pid}" 2>/dev/null; do
    sleep 10
    current="$(primary_ipv4)"
    [[ -n "${current}" && "${current}" == "${address}" ]] || break
  done
  cleanup
  address_pid=""
  service_pid=""
  sleep 2
done
