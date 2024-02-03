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
role_list=$(get_role_names)

# If arguments are provided, use them as tags
tags=""
if [ $# -gt 0 ]; then
  tags="--tags $*"
fi

# Create a temporary playbook with the dynamic roles
temp_playbook=$(mktemp)
{
  printf -- "- hosts: localhost\n"
  printf -- "  gather_facts: true\n"
  printf -- "  become: true\n"
  printf -- "  roles:\n"
  while IFS= read -r role; do
    printf "    - { role: %s }\n" "$role"
  done <<< "$role_list"
} > "${temp_playbook}"

# Set ANSIBLE_ROLES_PATH to the roles directory
export ANSIBLE_ROLES_PATH="${WORKING_DIR}/roles"

# Run the Ansible playbook with the specified tags
ansible-playbook "${temp_playbook}" -i "${WORKING_DIR}/inventory" --ask-become-pass $tags

# DEBUG Print generated playbook
# echo "Generated dynamic playbook:"
# cat "${temp_playbook}"
# Remove the temporary playbook
rm "${temp_playbook}"