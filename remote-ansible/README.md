# This remote ansible project sets up an orange pi5 on Jammy 
To run:
```bash
./run.sh
```

or with tags
```bash
./run.sh install_vscode install_rustdesk
```

## Info
The playbook is automatically generated for you, it will contain:
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