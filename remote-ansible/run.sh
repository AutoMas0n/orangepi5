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

# Ensure roles are added in a specific order
ensure_order=( "system_update" "package_install" )

# If arguments are provided, use them as role names
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
  # Add the specific order roles if they exist in all_role_list
  for role in "${ensure_order[@]}"; do
    if printf '%s\n' "${all_role_list[@]}" | grep -qx "${role}"; then
      printf "    - { role: %s }\n" "$role" >> "${temp_playbook}"
    fi
  done

  # Add all other roles
  for role in ${all_role_list[@]}; do
    if ! printf '%s\n' "${ensure_order[@]}" | grep -qx "${role}"; then
      printf "    - { role: %s }\n" "$role" >> "${temp_playbook}"
    fi
  done
fi

# Set ANSIBLE_ROLES_PATH to the roles directory
export ANSIBLE_ROLES_PATH="${WORKING_DIR}/roles"

# DEBUG Print generated playbook
# echo "Generated dynamic playbook:"
cat "${temp_playbook}"
# Run the Ansible playbook
ansible-playbook "${temp_playbook}" -i "${WORKING_DIR}/inventory" --ask-become-pass

# Remove the temporary playbook
rm "${temp_playbook}"