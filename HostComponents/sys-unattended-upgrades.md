To set up automatic updates on an Ubuntu server, you can use the `unattended-upgrades` package. Follow these steps:

1. Install `unattended-upgrades` if it's not already installed:
```bash
sudo apt-get update
sudo apt-get install unattended-upgrades
```

2. Enable automatic updates by editing the configuration file:
```bash
sudo dpkg-reconfigure -plow unattended-upgrades
```
When prompted, choose "Yes" to enable automatic updates.

3. For more granular configuration, you can manually edit the `/etc/apt/apt.conf.d/50unattended-upgrades` file. Use your preferred text editor:
```bash
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```
Here you can specify which package categories to update and other options.

4. You can also create or edit the `/etc/apt/apt.conf.d/20auto-upgrades` file to configure the frequency of the updates:
```bash
sudo nano /etc/apt/apt.conf.d/20auto-upgrades
```
And add the following lines to set the update interval:
```bash
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
```
This configuration will check for updates daily and clean up every week.

5. After configuring, you can simulate an unattended upgrade to check for any issues:
```bash
sudo unattended-upgrade --dry-run --debug
```

6. To ensure that the automatic updates are applied, you may want to enable and start the `unattended-upgrades` service:
```bash
sudo systemctl enable unattended-upgrades
sudo systemctl start unattended-upgrades
```

Make sure to review your configurations to ensure that they meet your specific requirements for automatic updates.