from nornir_scrapli.tasks import send_commands
from nornir import InitNornir
from nornir.core.filter import F
from datetime import datetime
from pathlib import Path
import getpass
import argparse
import os

"""
A network interface for executing ad-hoc show commands across groups of devices based on platform, role, site, their combination, or a list of devices.
The ouput is saved in a site- & time-stamped folder.

How to Use:
1. Define your hosts file - This is your network devices' inventory
2. Execute the script by providing the following arguments:
    Requred arguments - site & role OR devices, commands, primary_user
    Optional arguments - platform, backup_user, maintenance

Example 1 - Execute "show run" & "show ver" against all LEAFs (role) in WARSAW (site)
$python network_interface.py -s WARSAW -r LEAF -c "show run" "show ver" -pu <username>

Example 2 - Execute "show run" & "show ver" against all SPINEs (role) in all sites running Arista eos
$python network_interface.py -s ALL -r SPINE -p eos -c "show run" "show ver" -pu <username>

Example 3 - Execute "show run" & "show ver" against all devices in XYZ site running nxos
with backup credentials in case some devices may not work with the primary credentials
$python network_interface.py -s XYZ -r ALL -p nxos -c "show run" "show ver" -pu <primary_username> -bu <backup_username>

"""

class Network_Interface():

    def __init__(
        self, 
        site = None, 
        role = None, 
        devices = None, 
        platform = None, 
        commands = None, 
        primary_user = None, 
        backup_user = None, 
        maintenance = None,
        ):

        self.site = site
        self.role = role
        self.devices = devices
        self.platform = platform
        self.commands = commands
        self.primary_user = primary_user
        self.backup_user = backup_user
        self.maintenance = maintenance
        self.output_counter = 0

    def main(self):
        timestamp = "{:%Y-%m-%d_%H-%M}".format(datetime.now())
        # Initiate Nornir using the regular config
        nr = InitNornir(
            config_file=((Path(__file__).parent)/"nornir_data/config.yaml").resolve(), core={"raise_on_error": True})

        # If maintenance argument is present, use the maintenance config & hosts.
        if self.maintenance:
            nr = InitNornir(
                config_file=((Path(__file__).parent)/"nornir_data/maint_config.yaml").resolve(), core={"raise_on_error": True})

        # Get the primary/secondary credentials to authenticate the SSH connections
        if self.primary_user:
            self.primary_password = getpass.getpass(prompt="Primary Password: ")
            nr.inventory.defaults.username = self.primary_user
            nr.inventory.defaults.password = self.primary_password
        if self.backup_user:
            self.backup_password = getpass.getpass(prompt="Backup Password: ")

        # If devices/site/role haven't been specified - display error and exit
        if self.devices is None and (self.site is None or self.role is None):
            print(
                "Please specify the targeted devices or filter groups of devices by site and role")
            exit()

        # If devices have been specified, filter only for those devices
        elif self.devices:
            # Create a site- & time-stamped directory for the output
            self.site = "ALL"
            self.mkdir_now(timestamp=timestamp)

            self.devices = [device.upper() for device in self.devices]
            nr = nr.filter(F(hostname__any=self.devices))

        elif self.site and self.role:
            self.site = self.site.upper()
            self.role = self.role.upper()

            # Create a site- & time-stamped directory for the output
            self.mkdir_now(timestamp=timestamp)

            # If platform argument is present, filter only for hosts running the desired platform
            if self.platform:
                nr = nr.filter(platform=self.platform.lower())

            # If neither argument is "ALL", issue commands against all devices with the provided role & at the provided site
            if self.site != "ALL" and self.role != "ALL":
                nr = nr.filter(site=self.site, role=self.role)

            # If the site argument is not "ALL", issue commands against all devices within the provided site
            elif self.site != "ALL":
                nr = nr.filter(site=self.site)

            # If the role argument is not "ALL", issue commands against all devices of the provided role
            elif self.role != "ALL":
                nr = nr.filter(role=self.role)

        print(f"Number of Targeted Hosts: {len(nr.inventory.hosts)}.\n")

        result = nr.run(task=self.execute_commands, timestamp=timestamp, creds_type="Primary")
        if result.failed and self.backup_user:
            nr.inventory.defaults.username = self.backup_user
            nr.inventory.defaults.password = self.backup_password
            result = nr.run(task=self.execute_commands, on_failed=True, on_good=False, 
                                 timestamp=timestamp, creds_type="Backup")

        # Print what commands have been issued, and against how many devices.
        print(f"Commands Sent: {self.commands}\n")
        print(f"The Number of Saved Files: {self.output_counter}\n")

    # Make a time- & site stamped directory for the output
    def mkdir_now(self, timestamp):
        location = f"output/{self.site}/{timestamp}"
        try:
            os.makedirs(location)
            print(f"\nThe Output Will Be Saved in: {location}\n")
        except OSError as err:
            print("Encountered the following error when creating an output directory")
            print(err)

    # Connect to the devices & send the commands. If the output is present, pass it to the save_output function
    def execute_commands(self, task, timestamp, creds_type):
        try:
            result = task.run(task=send_commands,
                                commands=list(self.commands))
            if result.result:
                self.save_output(task, result=result.result, timestamp=timestamp)
        except Exception as err:
            print(
                f"{task.host} Failed to Provide the Output with {creds_type} Credentials\n")
            print(err)

    # Safe the output in the site-stamped & time-stamped directory.
    def save_output(self, task, result, timestamp):
        with open(f"output/{self.site}/{timestamp}/{task.host}.txt", "w") as f:
            f.write(result)
        self.output_counter += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provide arguments to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=False,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=False,
                        help='The role of the targeted devices (SPINE/LEAF/...)')
    parser.add_argument('-d', '--devices', type=str, nargs='+', required=False, help='A single device, or a list of devices to be targeted')
    parser.add_argument('-p', '--platform', type=str, required=False,
                        help='The platform of the targeted devices (eos/iosxe/iosxr/nxos)')
    parser.add_argument('-c', '--commands', type=str, nargs='+',
                        required=True, help='The commands to be run against the devices')
    parser.add_argument('-pu', '--primary_user', type=str,
                        required=True, help='The primary username used to SSH into the targeted devices')
    parser.add_argument('-bu', '--backup_user', type=str,
                        required=False, help='The backup username, to be used if the primary fails')
    parser.add_argument('-m', '--maintenance', type=str, required=False,
                        help='Whether this is for a maintenance (y). This will use the maintenance config/hosts instead')

    args = parser.parse_args()

    Net_Int = Network_Interface(
        args.site, args.role, args.devices, args.platform, args.commands, args.primary_user, args.backup_user, args.maintenance)
    Net_Int.main()