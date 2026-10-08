# Install Blank Box on Windows

The available Windows package is the older experimental 0.1.0-beta.8 release for one Windows 10/11 x64 account. Use its `-windows-x64.zip` package. It includes Python, so you do not need to install a runtime or a CD-ripping application separately. This release runs in the foreground or after user sign-in; it is not a native Windows service. The smaller source ZIP is for advanced users who will install Python 3.10+ themselves.

## 1. Extract and run setup

Use `blankbox-community-...-windows-x64.zip` on Windows 10/11 x64. The generic Community ZIP is for Linux/Docker, and the source ZIP is for a source build. In File Explorer, right-click the Windows ZIP and choose **Extract All**. Open the extracted folder until you can see `setup-windows.cmd` and `RELEASE.json`, then double-click `setup-windows.cmd`. Running setup from inside the ZIP preview does not install Blank Box. For a restore-only test of an existing library, first read [Recovery](../RECOVERY.md) and use a separate empty data folder.

If Windows does not open the launcher, open PowerShell in that folder and run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\setup-windows.ps1
```

The wizard asks whether to install/update or uninstall, which port to use, whether other devices on the trusted home network may connect, and whether Blank Box should start when you sign in.

After setup, start Blank Box:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\BlankBox\start-windows.ps1"
```

Keep that window open. Use Ctrl+C for a graceful stop. Open `http://127.0.0.1:25265`. To find the recovery key, paste this path into File Explorer's address bar, then open the file with a text editor:

```text
%LOCALAPPDATA%\BlankBox\data\access-key.txt
```

## Installed files

```text
%LOCALAPPDATA%\BlankBox\
├── releases\       immutable application versions and private Python runtime
├── data\           catalog, key, imported media, upgrade snapshots
├── config.json
├── current.json
├── start-windows.ps1
├── rollback-windows.ps1
└── uninstall-windows.ps1
```

Edit `config.json` while Blank Box is stopped to change source folders, backup destination, listener, or port.

## Advanced manual installation

The setup wizard is recommended. For scripting, the lower-level installer is still available; `-RegisterStartupTask` adds the per-user logon task:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\install-windows.ps1 -RegisterStartupTask
```

This is a per-user logon task, not a Windows service.

## Upgrade and rollback

Stop Blank Box, extract the newer package, run `setup-windows.ps1`, and choose **Install or update**. Existing data and configuration are preserved and a pre-upgrade catalog snapshot is created.

Roll back the most recent compatible upgrade with:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\BlankBox\rollback-windows.ps1"
```

## Uninstall

Stop Blank Box, then run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\BlankBox\uninstall-windows.ps1"
```

Uninstall removes the matching startup task and retains all application, configuration, data and unrelated files. Permanent removal is a separate manual action after verifying a backup. Keep the data until you have verified a separate restore.

## Other devices and friendly names

Windows local-network discovery varies by network and installed discovery services. Use the computer's local name or IP with port `25265`, and allow only private-network access in Windows Firewall. `blankbox.local` is not promised by the experimental Windows package. See [Local addresses and networking](NETWORKING.md).

This Windows package remains experimental. It cannot open schema 22 or 23 catalogs from the current Linux/Docker releases.

## Audio-CD import (experimental)

Blank Box can enumerate Windows optical drives and use Windows' read-only CD APIs to create lossless WAV tracks, linked to the physical CD in your library. It does not require a separate CD-ripping program or online metadata service. WAV uses more storage than FLAC; the browser player can use the imported tracks, and you can edit placeholder names afterward. We haven’t tested this adapter with a real Windows PC and audio CD. Keep the original disc and an independent backup; try an import, playback and restore on your own drive before relying on it. The Windows x64 offline package includes its own Python runtime.
