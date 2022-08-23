from nornir_utils.plugins.functions import print_result
from nornir_scrapli.tasks import send_commands
from nornir import InitNornir
from nornir.core.filter import F
from datetime import datetime
import getpass
import argparse
import os


class Network_Interface():

    def __init__(self, site=None, role=None, devices=None, platform=None, commands=None, tacacs_user=None, local_user=None, maintenance=None):
        self.site = site
        self.role = role
        self.devices = devices
        self.platform = platform
        self.commands = commands
        self.tacacs_user = tacacs_user
        self.local_user = local_user
        self.maintenance = maintenance
        self.nr = InitNornir(
            config_file='/home/kamil/Network_Interface/nornir_data/config.yaml')
        self.date = datetime.now()
        self.output_counter = 0

    def main(self):
        # If maintenance argument is present, switch to maintenance config & hosts, instead of the regular ones.
        if self.maintenance:
            self.nr = InitNornir(
                config_file="/home/kamil/Network_interface/nornir_data/maint_config.yaml")
        if self.local_user is None and self.tacacs_user is None:
            print("Please provide a local or tacacs username when running the script")
            print("For local username, use -lu parameter, like -lu 'your_local_username'")
            print(
                "For tacscs username, use -tu parameter, like -tu 'your_tacacs_username'")
            exit()
            # Gather user's login details to authenticate SSH connections
        if self.local_user:
            self.local_password = getpass.getpass(prompt="Local Password: ")
        if self.tacacs_user:
            self.tacacs_password = getpass.getpass(prompt="Tacacs Password: ")
            self.nr.inventory.defaults.username = self.tacacs_user
            self.nr.inventory.defaults.password = self.tacacs_password

        # If no devices/site/role have been specified - Display error and exit
        if self.devices is None and (self.site is None or self.role is None):
            print(
                "Please specify the targeted devices or filter groups of devices by site and role")
            exit()

        # If devices have been specified, filter only for those devices
        elif self.devices:
            # Create a site- & time-stamped directory for the output
            self.site = "ALL"
            self.mkdir_now()

            self.devices = [device.upper() for device in self.devices]
            self.nr = self.nr.filter(F(hostname__any=self.devices))

        elif self.site and self.role:
            self.site = self.site.upper()
            self.role = self.role.upper()

            # Create a site- & time-stamped directory for the output
            self.mkdir_now()

            # If platform argument is present, filter only for hosts running the desired platform
            if self.platform:
                self.nr = self.nr.filter(platform=self.platform.lower())

            # If neither argument is "ALL", issue commands against all devices with the provided role & at the provided site
            if self.site != "ALL" and self.role != "ALL":
                self.nr = self.nr.filter(site=self.site, role=self.role)

            # If the site argument is not "ALL", issue commands against all devices within the provided site
            elif self.site != "ALL":
                self.nr = self.nr.filter(site=self.site)

            # If the role argument is not "ALL", issue commands against all devices of the provided role
            elif self.role != "ALL":
                self.nr = self.nr.filter(role=self.role)

        print(f"There are {len(self.nr.inventory.hosts)} targeted hosts.\n")

        result = self.nr.run(task=self.execute_commands, creds_type="Tacacs")
        if result.failed and self.local_user:
            self.nr.inventory.defaults.username = self.local_user
            self.nr.inventory.defaults.password = self.local_password
            result = self.nr.run(task=self.execute_commands,
                                 on_failed=True, on_good=False, creds_type="Local")

        # Print what commands have been issued, and against how many devices.
        print(f"Commands sent: {self.commands}")
        print(f"The number of saved outputs: {self.output_counter}\n")

    # Make a directory for the output

    def mkdir_now(self) -> "Directory":
        location = f"output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}"
        try:
            os.makedirs(location)
            print(f"\nThe output will be saved in: {location}\n")
        except OSError as err:
            print("Encountered the following error when creating an output directory")
            print(err)

    # Ping the host to check if it's reachable
    def is_host_alive(self, task):
        test = os.system(f"ping -c 3 {task.host} >/dev/null 2>&1")
        if test == 0:
            return True
        else:
            return False

    # Connect to the devices & send the commands. If the output is present, pass it to the save_output function
    def execute_commands(self, task, creds_type):
        if self.is_host_alive(task):
            try:
                result = task.run(task=send_commands,
                                  commands=list(self.commands))
                if result.result:
                    self.save_output(task, result=result.result)
            except Exception as err:
                print(
                    f"{task.host} Failed to Provide Output with {creds_type} Credentials\n")
                print(err)
        else:
            print(f"{task.host} Unreachable")

    # Safe the output in the site-stamped & time-stamped directory.
    def save_output(self, task, result):
        with open(f"output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{task.host}.txt", "w") as f:
            f.write(result)
        self.output_counter += 1


if __name__ == '__main__':
    # Requred arguments - site & role OR devices, commands, tacacs_user or local_user
    # Optional arguments - platform, maintenance
    parser = argparse.ArgumentParser(
        description='Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=False,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=False,
                        help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    parser.add_argument('-d', '--devices', type=str, nargs='+' required=False, help='A single device, or a list of devices to be targeted')
    parser.add_argument('-p', '--platform', type=str, required=False,
                        help='The platform of the targeted devices (eos/iosxe/iosxr/nxos)')
    parser.add_argument('-c', '--commands', type=str, nargs='+',
                        required=True, help='The commands to be run against the devices')
    parser.add_argument('-tu', '--tacacs_user', type=str,
                        required=False, help='The tacacs username')
    parser.add_argument('-lu', '--local_user', type=str,
                        required=False, help='The local username')
    parser.add_argument('-m', '--maintenance', type=str, required=False,
                        help='Whether this is for a specific maintenance (y). This will use the maintenance config/hosts instead')

    args = parser.parse_args()

    Net_Int = Network_Interface(
        args.site, args.role, args.devices, args.commands, args.tacacs_user, args.local_user, args.maintenance)
    Net_Int.main()
