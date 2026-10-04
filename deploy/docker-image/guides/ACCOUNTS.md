# Sign-in and password recovery

Blank Box uses a local username and password. You can also enable optional OpenID Connect (OIDC) sign-in through an identity provider you control. Local sign-in and password recovery remain available when that provider is offline.

This is one shared household account. Separate user accounts, per-user libraries and individual permissions are not available yet. Linking OIDC adds a sign-in option for that same account.

## Forgotten password

1. Select **Forgot password? Use recovery key** on the sign-in screen.
2. Enter your username, admin recovery key, and a new password twice.
3. Select **Reset password**.

Your library stays intact. Remembered devices are signed out, and any OIDC identity is disconnected. Sign in locally and link it again when you are ready.

The recovery key is stored in `access-key.txt` inside your Blank Box data folder. Keep a private copy separately from the computer. If you have server access, you can read the original privately:

- Native Linux: normally `/var/lib/blankbox/access-key.txt`; the installer prints the actual path.
- Docker: `/data/access-key.txt` inside the container. From your installation folder, run:

```sh
docker compose exec -T blankbox python3 -c 'print(open("/data/access-key.txt").read().strip())'
```

- Windows: normally `%LOCALAPPDATA%\BlankBox\data\access-key.txt`.
- Direct Python: `access-key.txt` in the data folder you selected.

Never post your recovery key in an issue or support message. Portable library recovery creates a new account and recovery key; it does not restore passwords or identity-provider credentials.

## Optional OIDC sign-in

First claim your local account and confirm that password sign-in works. Register Blank Box as an application with your provider. Use authorization code flow with PKCE S256 and RS256-signed ID tokens. Register the exact callback address ending in `/api/oidc/callback`.

Use HTTPS for the provider and Blank Box callback. HTTP is accepted only for loopback development. OIDC does not configure a reverse proxy, certificates, or outside-home access.

Add this `oidc` object to your existing server JSON configuration, keeping your existing data, sources, backup, host and port settings:

```json
{
  "oidc": {
    "issuer": "https://identity.example.com/application/o/blankbox/",
    "clientId": "blankbox",
    "redirectUri": "https://blankbox.example.com/api/oidc/callback",
    "name": "My identity provider"
  }
}
```

Copy the issuer exactly from your provider; a trailing slash matters. For a confidential client, add `clientSecretFile` with an absolute path to a separate private text file containing the client secret. On Linux, that file must be readable only by the Blank Box account. The client uses `client_secret_basic`; a public client uses PKCE without a secret. Keep these configuration and secret files out of source control.

For Docker, place the same OIDC object as a single-line JSON value in your private `.env` file under `BLANKBOX_OIDC`. The supplied Compose file passes it to Core. A secret file must also be accessible inside the container, for example `/data/oidc-client-secret` in its private data folder. Preserve your existing storage and numeric user settings when recreating the container.

After restarting your own installation with the configuration:

1. Sign in with your local password.
2. Open **Settings → General → Account sign-in and recovery**.
3. Enter your local password and select **Link identity provider**.
4. Complete sign-in at your provider.

After linking, the Blank Box sign-in screen offers your provider alongside local sign-in. Only the explicitly linked identity can open this account. Matching an email address does not grant access. No access tokens, refresh tokens, or provider passwords are retained.

Use the same settings section and your local password to unlink. Signing out of Blank Box does not sign you out of your provider. Portable exports and library recovery omit identity bindings; configure and link the provider again on a recovered installation.

Check sign-in, callback addresses and recovery with your provider before relying on it. Keep local password sign-in available in case the provider is offline.
