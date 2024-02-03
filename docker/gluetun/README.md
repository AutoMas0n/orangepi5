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
export PIA_TOKEN=$(source ../secrets && sudo PIA_USER=$PIA_USER PIA_PASS=$PIA_PASS ./get_token.sh | grep -oP 'PIA_TOKEN=\K\S+')
export PIA_TOKEN=$(source ../secrets && sudo PIA_USER=$PIA_USER PIA_PASS=$PIA_PASS ./get_region_and_token.sh | grep -oP 'PIA_TOKEN=\K\S+')
sudo PIA_CONNECT=false PIA_TOKEN=$PIA_TOKEN ./connect_to_wireguard_with_token.sh

sudo ./run_setup.sh
```