#!/bin/bash

# Install expect if not already installed
if ! command -v expect &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y expect
fi

# Create an expect script to interact with orangepi-config
expect -d <<END
set timeout -1
# exp_internal 1 ;# Enable expect internal debugging

spawn sudo orangepi-config

# Wait for the first screen
expect "Finish" { sleep 4; send -- "\r" }

# Wait for the second screen
expect "Finish" { sleep 4; send -- "\r" }

# Navigate to the 7th option
expect "Finish" { sleep 4; send -- "7\r" }

# Select the option
expect "Finish" { sleep 4; send -- "\r" }

# Confirm the selection
expect "Finish" { sleep 4; send -- "\r" }

# Wait for operations to complete
sleep 10

# Exit the orangepi-config tool
send -- "\003" ;# This sends Ctrl-C to exit if necessary
expect eof
END

# Reminder message
echo "Please remember to remove the SD card!"

# Shutdown the system
sudo shutdown -h now