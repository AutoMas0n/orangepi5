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

## Install Prereqs and run Gluetun
1. first
```
cd docker/gluetun
```
2. https://github.com/qdm12/gluetun-wiki/issues/35
```bash
source /etc/profile && export PATH=$PATH:$(go env GOPATH)/bin
go install github.com/kylegrantlucas/pia-wg-config@latest
source ../../secrets && pia-wg-config -o ../../wg0.conf -r "ca_toronto" $PIA_USER $PIA_PASS # needs a retry

sudo docker-compose up -d #-d indicates background process
sudo docker logs gluetun
# OR
sudo docker-compose up 

```

## TODO need to fix dir context - location

## Run gluetun container with entrypoint
```bash
sudo chmod 777 /home/orangepi/Github/orangepi5/wg0.conf
sudo docker run --name gluetun2 --user root --entrypoint /bin/sh -it -v /home/orangepi/Github/orangepi5/wg0.conf:/gluetun/wireguard/wg0.conf qmcgaw/gluetun
sudo docker rm gluetun2
```