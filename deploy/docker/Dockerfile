FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

LABEL org.opencontainers.image.title="Blank Box Community" \
      org.opencontainers.image.description="Private household media and ownership system" \
      org.opencontainers.image.url="https://blankbox.org/self-hosted/" \
      org.opencontainers.image.licenses="LicenseRef-Blank-Box-Personal-Use"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BLANKBOX_DATA=/data \
    BLANKBOX_HOST=0.0.0.0 \
    BLANKBOX_PORT=25265

RUN groupadd --gid 10001 blankbox \
    && useradd --uid 10001 --gid 10001 --home-dir /data --no-create-home --shell /usr/sbin/nologin blankbox \
    && install -d -o blankbox -g blankbox -m 0700 /data \
    && install -d -o root -g root -m 0755 /opt/blankbox

WORKDIR /opt/blankbox
COPY --chown=root:root server.py file_safety.py runtime_lock.py release_files.py release_auth.py release-trust.json artwork.py metadata.py catalog_details.py metadata_pack.py metadata_indexed_pack.py metapack_identity.py disc_id.py collecting.py completion.py edition_completion.py library_collections.py barcodes.py collection_discovery.py bundled_metadata.py refresh_schedule.py library_browse.py folder_monitor.py commerce.py tv_catalog.py catalog_lists.py local_clues.py disc_import.py disc_import_linux.py reader.py restore.py doctor.py maintenance.py ./
COPY --chown=root:root retail_connectors ./retail_connectors
COPY --chown=root:root bundled-metadata ./bundled-metadata
COPY --chown=root:root VERSION RELEASE.json LICENSE THIRD-PARTY-NOTICES.md ./
COPY --chown=root:root third-party ./third-party
COPY --chown=root:root web ./web

# Application files are public release content, kept root-owned and read-only
# for runtime users. Private library data retains its separate owner-only modes.
# This permits Compose user overrides with a correctly owned /data bind mount.
RUN chmod -R u=rwX,go=rX /opt/blankbox

USER 10001:10001
EXPOSE 25265
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=90s --retries=3 \
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:25265/health/ready', timeout=2)"]

ENTRYPOINT ["python3", "/opt/blankbox/server.py"]
