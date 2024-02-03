- [List of VPN servers](#list-of-vpn-servers)
- [Starting Gluetun](#starting-gluetun)
- [TODO](#todo)

## List of VPN servers
```bash
# in docker/glueton/ 
sudo docker run --rm -v .:/gluetun qmcgaw/gluetun format-servers -private-internet-access
```

## Starting Gluetun
```bash
source secrets
docker-compose up -d
```

## TODO
```bash
git clone https://github.com/pia-foss/manual-connections.git
cd manual-connections
sudo ./run_setup.sh
```