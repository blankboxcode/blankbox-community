# Local addresses and networking

Blank Box Community listens on port `25265` by default. You can change it if that port is already in use.

## Choose direct access

The Linux setup wizard offers these three choices:

| Choice | Direct access | Address |
| --- | --- | --- |
| **1: On this computer** | Open Blank Box on the computer running it. | `http://127.0.0.1:25265` |
| **2: Trusted home network by IP** | Use that computer or another device on your trusted home network. | `http://SERVER-IP:25265` from the other device. |
| **3: The same network plus blankbox.local** | The same access as option 2, with a friendly local name where discovery works. | `http://blankbox.local:25265` or the server-IP address. |

Use the actual port selected during setup. `SERVER-IP` means the server's local address from its network settings or your router's device list; for example, `http://192.168.1.50:25265`. On any device, `127.0.0.1` means that device itself. Use it on the server, not on a phone trying to reach the server.

Options 2 and 3 still allow access on the server itself. None automatically enables Internet access from outside your home or disables outgoing Internet access. Optional online connections continue to use the computer's existing Internet connection. Option 1 limits direct connections to the server; a separately configured private proxy or VPN can still provide its own route to that listener.

## Optional friendly name and private access

| Address | Use |
|---|---|
| `http://127.0.0.1:25265` | Direct access on the computer running Blank Box. |
| `http://blankbox.local:25265` | Friendly same-network address when the optional Linux mDNS helper is enabled. |
| `http://SERVER-IP:25265` | Reliable same-network fallback. |
| Private Tailscale HTTPS address | Recommended for access away from the immediate LAN using an authenticated private network. |

The setup wizard does not install or configure a VPN, Tailscale Serve, router forwarding or a private HTTPS proxy. These require separate setup. The friendly `.local` name supplies neither outside-home access nor HTTPS.

Tailscale Serve still reaches Blank Box on your own server. It can forward a private HTTPS address to the app's localhost port; open the Serve address and its selected HTTPS port, which can differ from Blank Box's internal port. The catalog and media stay on your server. Direct Tailscale-IP access instead needs a listener or published port on that interface. See [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) for its separate configuration.

`blankbox.local` is multicast DNS, not a public website. It normally works only on the same broadcast network, can be blocked by guest Wi-Fi/VLAN isolation, and can conflict if two devices claim the same name. It does not provide HTTPS by itself.

A bare `http://blankbox.local` without `:25265` would require port 80 or a reverse proxy. The Community installer leaves existing ports 80 and 443 alone. Include `:25265` unless you configure your own reverse proxy.

## Change the port

- Native Linux: edit `/etc/blankbox/config.json`, restart `blankbox`, and update the local-name helper if enabled.
- Docker: set `BLANKBOX_PUBLISHED_PORT` in `.env`. Change the internal port only if you also update the Compose health and container settings.
- Windows: stop Blank Box and edit `%LOCALAPPDATA%\BlankBox\config.json`.
- Direct Python: use `--port NUMBER`.

## LAN safety

Binding to `127.0.0.1` accepts only connections from the same computer. Binding to `0.0.0.0` accepts connections reaching the computer's interfaces. Use LAN binding only on a trusted private network, retain authentication, and do not forward the port through a router. Tailscale Serve or another properly configured HTTPS reverse proxy is preferable for remote access.

## If another device cannot connect

1. Open Blank Box on the server first using `http://127.0.0.1:YOUR-PORT`. Keep the server on.
2. For option 2 or 3, try the server-IP address from a device on the same trusted network. Check that you used the server's current IP and the installed port. Guest Wi-Fi or network isolation may block access.
3. If the IP address works and `blankbox.local` does not, keep using the IP address. Check the optional discovery packages and local-name helper on the server.
4. If local access works but the IP address does not, check that setup used option 2 or 3, and review the host's private-network firewall settings. The installer does not open firewall or router ports. Do not forward a router port to solve a home-network connection problem.
