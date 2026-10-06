- [RESET](#reset)
- [List of VPN servers (dont need anymore)](#list-of-vpn-servers-dont-need-anymore)
- [Starting Gluetun](#starting-gluetun)
- [Install Prereqs and run Gluetun](#install-prereqs-and-run-gluetun)
- [TODO need to fix dir context - location](#todo-need-to-fix-dir-context---location)
- [Run gluetun container with entrypoint](#run-gluetun-container-with-entrypoint)

## RESET
```bash
sudo docker system prune -a
```

## List of VPN servers (dont need anymore)
```bash
# in docker/glueton/ 
sudo docker run --rm -v .:/gluetun qmcgaw/gluetun format-servers -private-internet-access
```

## Starting Gluetun
```bash
source secrets
docker-compose up -d
```

## WireGuard config: use docker/refresh-wireguard.sh

The old procedure below used `pia-wg-config`. That tool POSTs to
`privateinternetaccess.com/api/client/v2/addKey`, which now returns 404 - PIA moved
key registration to the VPN server itself, behind a token:

  1. `POST https://www.privateinternetaccess.com/api/client/v2/token` (form username/password)
  2. region -> wg server from `https://serverlist.piaservers.net/vpninfo/servers/v6`
  3. `GET https://<wg-hostname>:1337/addKey?pt=<token>&pubkey=<pubkey>` (TLS via ca.rsa.4096.crt)

`docker/refresh-wireguard.sh` wraps PIA's maintained implementation
(github.com/pia-foss/manual-connections) and installs the result as wg0.conf:

```bash
sudo ./docker/refresh-wireguard.sh            # ca_toronto
sudo ./docker/refresh-wireguard.sh ca_montreal # rotate region
```

gluetun runs as `VPN_SERVICE_PROVIDER=custom` + `VPN_TYPE=wireguard` with that file
mounted read-only. If the tunnel stops handshaking, re-run the script - PIA retires
server endpoints regularly.

## Old procedure (kept for reference, DO NOT USE - dead endpoint)
