TODO C<roNtAB
```bash
sudo crontab -l
0 3 * * * cd /home/orangepi/Github/orangepi5/docker && /home/orangepi/Github/orangepi5/docker/run.sh
0 0 * * * /home/orangepi/Github/orangepi5/docker/docker_pull.sh
30 4 * * 0 /usr/bin/docker system prune -f >> /var/log/docker-prune.log 2>&1
```

Note the prune is plain `docker system prune -f`, deliberately **without** `--volumes`: the stack uses bind mounts, so the flag buys little and can delete volumes belonging to any stopped container. It removes dangling images, stopped containers, unused networks and build cache. Unused *tagged* images (e.g. a retired service's) must be deleted explicitly with `docker image rm`.

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


# TODO DOCKER PULL
sudo docker pull qmcgaw/gluetun
sudo docker pull lscr.io/linuxserver/jackett
sudo docker pull lscr.io/linuxserver/qbittorrent
sudo docker pull lscr.io/linuxserver/jellyfin
