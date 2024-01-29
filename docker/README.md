```bash
sudo docker run --name hbbr -v ./data:/root -td --net=host rustdesk/rustdesk-server hbbr
```
# Pending ansible
sudo docker image pull rustdesk/rustdesk-server
sudo docker run --name hbbs -v ./data:/root -td --net=host rustdesk/rustdesk-server hbbs -r 192.168.2.155
# TODO start hbbs, restart or modify run command to generate the ./id_ed25519.pub
sudo docker exec -it --user root hbbr /bin/bash
ywCjf1fDg**********
cat ./id_ed25519.pub

# This has to be retested, looks like the data folder is generated with ./id_ed25519.pub on the host machine

On client & server, use sudo to change the settings to include 
ID Server: `192.168.2.155` Relay Server: `192.168.2.155` Key : ywCjf1fDg**********