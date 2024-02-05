#!/bin/bash

# Get the current working directory
WORKING_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to get a list of role names from the roles directory
get_role_names() {
  for role_path in "${WORKING_DIR}/roles"/*; do
    if [ -d "${role_path}" ]; then
      basename "${role_path}"
    fi
  done
}

# Convert the role names to a YAML list
all_role_list=$(get_role_names)

# Create a temporary playbook
temp_playbook=$(mktemp)
{
  printf -- "- hosts: localhost\n"
  printf -- "  gather_facts: true\n"
  printf -- "  become: true\n"
  printf -- "  roles:\n"
} > "${temp_playbook}"

# If arguments are provided, use them as role names, otherwise use all roles
if [ $# -gt 0 ]; then
  for role in "$@"; do
    if printf '%s\n' "${all_role_list[@]}" | grep -qx "${role}"; then
      printf "    - { role: %s }\n" "$role" >> "${temp_playbook}"
    else
      echo "Role '${role}' does not exist."
      rm "${temp_playbook}"
      exit 1
    fi
  done
else
  for role in ${all_role_list[@]}; do
    printf "    - { role: %s }\n" "$role" >> "${temp_playbook}"
  done
fi

# Set ANSIBLE_ROLES_PATH to the roles directory
export ANSIBLE_ROLES_PATH="${WORKING_DIR}/roles"

# Run the Ansible playbook
ansible-playbook "${temp_playbook}" -i "${WORKING_DIR}/inventory" --ask-become-pass

# DEBUG Print generated playbook
# echo "Generated dynamic playbook:"
# cat "${temp_playbook}"
# Remove the temporary playbook
rm "${temp_playbook}"