# Jackett

TorrentLeech is the configured indexer. Its state lives in
`~/docker-data/Jackett/` (gitignored, covered by `scripts/backup.sh`), so it is
**not** reproduced by cloning this repo — use the script below after a rebuild.

## Re-adding the indexer

```bash
sudo ./docker/jackett/apply-indexers.sh
```

It reads `TL_USER` / `TL_PASS` from the gitignored `secrets` file and POSTs them
to Jackett's API. Verified end to end: `HTTP 204`, then a `matrix` search
returns ~35 TorrentLeech releases.

## Two things that cost real time

* **The login is the bare username, not the email.** `4543562a`, *not*
  `4543562a@gmail.com` — TorrentLeech rejects the email form with
  "Invalid Username/password combination", which Jackett surfaces as HTTP 500
  because *it validates the login while saving*.
* **The config payload is an array of `{id, value}`.** Jackett matches fields by
  `id` (`ConfigurationData.LoadConfigDataValuesFromJson`); `{name, ...}` or a
  plain dict gives a cast error.

## qBittorrent's search tab

The Jackett search plugin is enabled and its config is correct *inside* the
container, and the plugin returns results when run directly. The WebUI search
tab still comes back empty — `docker-data/qBittorrent/nova3/engines/jackett.json`
is a 0-byte file on the host that the container's bind mount shadows. Searching
via Jackett's own UI at `:9117` works fine; fixing the search tab is optional.
