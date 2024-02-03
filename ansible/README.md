To run:
```bash
ansible-playbook playbook.yml -i inventory --ask-become-pass
```

or with tags
```bash
ansible-playbook playbook.yml -i inventory --ask-become-pass --tags "install_vscode"
```

NEW
```bash
ansible-playbook playbook.yml -i inventory --extra-vars='ansible_become_pass=******' --tags "start_vnc"
```

## Issues
