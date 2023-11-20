- [**Install Ansible:**](#install-ansible)
  - [**Setup Ansible Project:**](#setup-ansible-project)
  - [**Install Watchtower:**](#install-watchtower)

# **Install Ansible:**

1. Open a terminal on your Orange Pi 5.
2. Update the package list:

```bash
sudo apt update
```

3. Install Ansible:

```bash
sudo apt install ansible -y
```

## **Setup Ansible Project:**

1. Create a directory for your Ansible project:

```bash
mkdir ~/ansible-project
cd ~/ansible-project
```

2. Create a hosts inventory file (e.g., `hosts.ini`):

```bash
echo "localhost ansible_connection=local" > hosts.ini
```

3. Create a playbook file (e.g., `playbook.yml`) and add your tasks. You can start with the Docker installation example you provided:

```bash
nano playbook.yml
```

Paste your YAML content into the file and save it (`CTRL+O`, `Enter`, `CTRL+X`).

**Run Ansible Playbook:**

1. Run your playbook with the following command:

```bash
ansible-playbook -i hosts.ini playbook.yml
```

## **Install Watchtower:**

With Docker installed, you can set up Watchtower using a `docker-compose.yml` file or a Docker run command.

**Using `docker-compose.yml`**:

1. Create a `docker-compose.yml` file:

```bash
nano docker-compose.yml
```

2. Add the following content to the file:

```yaml
version: '3'
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --schedule "0 0 4 * * *"
```

3. Start Watchtower with:

```bash
docker-compose up -d
```

**Using Docker run command**:

Run the following command in your terminal:

```bash
docker run -d --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --cleanup --schedule "0 0 4 * * *"
```

The `--schedule` option is set to check for updates at 4 AM every day. Adjust the schedule to fit your needs.

Remember to replace `/var/run/docker.sock` with the correct path if your Docker socket is located elsewhere.