To run:
```bash
export SSH_USER=orangepi SSH_PASS=orangepi
sudo -E ./run.sh 192.168.2.215
```

or with roles
```bash
export SSH_USER=orangepi SSH_PASS=orangepi
sudo -E ./run.sh 192.168.2.215 my_ip
```

## Info
The playbook is automatically generated for you, it will generate dynamic playbook:
```yaml
- hosts: localhost
  gather_facts: true
  become: true
  roles:
    - system_update
    - disable_update_notifier
    - package_install
    - flatpak_repo
    - install_rustdesk
    - install_vscode
    - docker
```
The script will add the roles based on the files found so that you dont have to edit the playbook to add new roles

/tmp dir will be where the playbook lives temporarily, then deleted