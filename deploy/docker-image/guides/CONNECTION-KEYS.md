# Connect Jellyfin or Plex to Blank Box

Connect an existing Jellyfin or Plex server through **Settings → Connections**. Enter an address reachable from the computer running Blank Box, paste the credential into the matching field and choose **Sync**. Saving a website address alone gives you a launch shortcut; syncing requires the credential. Syncing reads the catalog and adds links that open playback in the connected app. The server’s library files stay unchanged.

## Jellyfin API key

1. Sign in to your Jellyfin server with an administrator account.
2. Open **Dashboard → Advanced → API Keys**. Choose **Create API Key** or the **+** button. Name it `Blank Box` so you can identify it later. The exact labels can vary with Jellyfin Web versions.
3. Copy the new key once and paste it into **Jellyfin API key** in Blank Box. Enter the Jellyfin server address, usually `http://server-address:8096`, then choose **Sync Jellyfin**.

Jellyfin's [official Web interface source](https://github.com/jellyfin/jellyfin-web/blob/master/src/strings/en-us.json) contains the API-key controls. Keep the key private; revoke it in Jellyfin if the device is no longer trusted. Use an address the Blank Box host can reach, especially when Jellyfin runs in a separate container.

## Plex token

1. Sign in to the Plex Web App with the account that can access your server.
2. Open an item in that server's library, choose **Get Info**, then **View XML**. Plex's [token instructions](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) describe this path.
3. Copy only the value of `X-Plex-Token` from the XML page URL. Enter the Plex server address, usually `http://server-address:32400`, and paste the value into **Plex token** in Blank Box. Choose **Sync Plex**.

Plex describes the token obtained this way as temporary. If a later sync stops authenticating, obtain a fresh token. The manual-token connection is experimental. Do not paste the token into support tickets, screenshots, or a public URL.

## If sync fails

- Confirm the address opens from the Blank Box **host**, not just your phone or laptop. A container may need a host or network address instead of `localhost`.
- Confirm the credential belongs to the server and account with access to the desired libraries.
- Check that the source server is running, then try **Sync** again. A connection failure does not erase your Blank Box library.
- Keep source ports private or behind your existing private access setup. Do not expose a media server solely to make this connection work.
