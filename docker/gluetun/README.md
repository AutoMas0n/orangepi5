- [List of VPN servers (dont need anymore)](#list-of-vpn-servers-dont-need-anymore)
- [Starting Gluetun](#starting-gluetun)
- [Install Prereqs and run Gluetun](#install-prereqs-and-run-gluetun)

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

## Install Prereqs and run Gluetun
https://github.com/qdm12/gluetun-wiki/issues/35
```bash
source /etc/profile && export PATH=$PATH:$(go env GOPATH)/bin
go install github.com/kylegrantlucas/pia-wg-config@latest
source ../secrets && pia-wg-config -o wg0.conf $PIA_USER $PIA_PASS

sudo PIA_USER=$PIA_USER PIA_PASS=$PIA_PASS docker-compose up -d
sudo docker logs gluetun
```