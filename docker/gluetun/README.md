- [List of VPN servers](#list-of-vpn-servers)
- [Starting Gluetun](#starting-gluetun)

## List of VPN servers
```bash
# in docker/glueton/ 
sudo docker run --rm -v .:/gluetun qmcgaw/gluetun format-servers -private-internet-access
```

## Starting Gluetun
```bash
source secrets \
sudo docker run -it --rm --cap-add=NET_ADMIN -e VPN_SERVICE_PROVIDER="private internet access" \
-e OPENVPN_USER=$OPENVPN_USER -e OPENVPN_PASSWORD=OPENVPN_PASSWORD \
-v gluetun:/gluetun \
-e SERVER_REGIONS=Netherlands qmcgaw/gluetun
```