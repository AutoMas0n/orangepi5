#!/bin/bash

# Ensure roles are added in a specific order
ensure_order=( "system_update" "disable_update_notifier" "package_install" )

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
  printf -- "- hosts: all\n"  # Changed from localhost to all to accommodate remote hosts
  printf -- "  gather_facts: true\n"
  printf -- "  become: true\n"
  printf -- "  roles:\n"
} > "${temp_playbook}"

# If arguments are provided, use them as role names
if [ $# -gt 1 ]; then  # Changed to greater than 1 to account for the target host argument
  for role in "${@:2}"; do  # Start from the second argument
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

# Check if a target host is provided (first argument)
TARGET_HOST=$1
SSH_USER=${SSH_USER:-}  # Expects SSH_USER environment variable
SSH_PASS=${SSH_PASS:-}  # Expects SSH_PASS environment variable

# Create a dynamic inventory file if TARGET_HOST is provided
if [ -n "${TARGET_HOST}" ]; then
  inventory_file=$(mktemp)
  echo "[remote]" > "${inventory_file}"
  echo "${TARGET_HOST} ansible_ssh_user=${SSH_USER} ansible_ssh_pass=${SSH_PASS} ansible_ssh_common_args='-o StrictHostKeyChecking=no'" >> "${inventory_file}"
else
  inventory_file="${WORKING_DIR}/inventory"
fi

# Run the Ansible playbook with the appropriate inventory
ansible-playbook "${temp_playbook}" -i "${inventory_file}" --ask-become-pass

# Remove the temporary playbook
rm "${temp_playbook}"

# Clean up the dynamic inventory file if one was created
if [ -n "${TARGET_HOST}" ]; then
  rm "${inventory_file}"
fi