# Local addresses and networking

We set Blank Box Community to listen on port `25265` by default. You can change it if that port is already in use.

## Address choices

| Address | Use |
|---|---|
| `http://127.0.0.1:25265` | Same computer only; safest default. |
| `http://blankbox.local:25265` | Friendly same-network address when the optional Linux mDNS helper is enabled. |
| `http://SERVER-IP:25265` | Reliable same-network fallback. |
| Private Tailscale HTTPS address | Recommended for access away from the immediate LAN using an authenticated private network. |

`blankbox.local` is multicast DNS, not a public website. It normally works only on the same broadcast network, can be blocked by guest Wi-Fi/VLAN isolation, and can conflict if two devices claim the same name. It does not provide HTTPS by itself.

A bare `http://blankbox.local` without `:25265` would require port 80 or a reverse proxy. Our Community installer leaves existing ports 80 and 443 alone. Include `:25265` unless you configure your own reverse proxy.

## Change the port

- Native Linux: edit `/etc/blankbox/config.json`, restart `blankbox`, and update the local-name helper if enabled.
- Docker: set `BLANKBOX_PUBLISHED_PORT` in `.env`. Change the internal port only if you also update the Compose health and container settings.
- Windows: stop Blank Box and edit `%LOCALAPPDATA%\BlankBox\config.json`.
- Direct Python: use `--port NUMBER`.

## LAN safety

Binding to `127.0.0.1` accepts only connections from the same computer. Binding to `0.0.0.0` accepts connections reaching the computer's interfaces. Use LAN binding only on a trusted private network, retain authentication, and do not forward the port through a router. Tailscale Serve or another reviewed HTTPS reverse proxy is preferable for remote access.
