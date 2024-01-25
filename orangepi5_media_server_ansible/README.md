To run:
```bash
ansible-playbook playbook.yml -i inventory --ask-become-pass
```

or with tags
```bash
ansible-playbook playbook.yml -i inventory --ask-become-pass --tags "start_vnc"
```