from supporting_scripts import get_credentials
from nornir_scrapli.tasks import send_commands, send_interactive
from nornir import InitNornir
from datetime import datetime
import argparse
import os


class Scrapli_Network_Interface():

    def __init__(self, site, role, platform=None, commands=None, interactive_commands=None, maintenance=None):
        self.site = site.upper()
        self.role = role.upper()
        self.platform = platform
        self.commands = commands
        self.interactive_commands = interactive_commands
        self.maintenance = maintenance
        self.nr = InitNornir(config_file='nornir_data/config.yaml')
        self.date = datetime.now()
        self.output_counter = 0

    def main(self):
        # If maintenance argument is present, switch to maintenance config & hosts, instead of the regular ones.
        if self.maintenance:
            self.nr = InitNornir(config_file='nornir_data/maint_config.yaml')

        # Retrieve the ssh login credentials from the encrypted file
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]

        # Create a site- & time-stamped directory for the output
        self.mkdir_now()

        # Configure interact events for commands that require interaction upon issuing
        if self.interactive_commands:
            interact_events = self.configure_interact_events()

        # If Site & Role arguments are "ALL", issue commands and/or interactive commands against entire hosts inventory
        if self.site == "ALL" and self.role == "ALL":
            if self.commands:
                result = self.nr.run(task=self.s_commands)
            if self.interactive_commands:
                interactive_result = self.nr.run(
                    task=self.s_int_commands, interact_events=interact_events)

        # If Site argument is "ALL", issue commands and/or interactive commands against all devices at the provided site
        elif self.site == "ALL":
            target = self.nr.filter(role=self.role)
            if self.commands:
                result = target.run(task=self.s_commands)
            if self.interactive_commands:
                interactive_result = target.run(
                    task=self.s_int_commands, interact_events=interact_events)

        # If Role argument is "ALL", issue commands and/or interactive commands against all devices with the provided role & at the provided site
        elif self.role == "ALL":
            target = self.nr.filter(site=self.site)
            if self.commands:
                result = target.run(task=self.s_commands)
            if self.interactive_commands:
                interactive_result = target.run(
                    task=self.s_int_commands, interact_events=interact_events)

        # If neither argument is "ALL", issue commands and/or interactive commands against all devices with the provided role & at the provided site
        else:
            target = self.nr.filter(site=self.site, role=self.role)
            if self.commands:
                result = target.run(task=self.s_commands)
            if self.interactive_commands:
                interactive_result = target.run(
                    task=self.s_int_commands, interact_events=interact_events)

        # Print what commands/interactive commands have been issued, and against how many devices, as well as where is the output saved
        if self.commands:
            print(f"Commands sent: {self.commands}\n")
        if self.interactive_commands:
            print(f"Interactive Commands sent: {self.interactive_commands}\n")
        print(f"the number of targeted devices: {self.output_counter}")
        print(
            f"The output can be found in: output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}")

    # Try to make a director for the expected output

    def mkdir_now(self) -> "Dir":
        try:
            os.makedirs(
                f"output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}")
        except OSError:
            pass

    # Connect to the devices & send the commands and if the output is present, pass the output to the save_output function
    def s_commands(self, task):
        result = task.run(task=send_commands, commands=self.commands)
        if result.result:
            self.save_output(task, result=result.result)

    # Connect to the devices & send the interactive commands, if the output is present, pass the output to the save_output function
    def s_int_commands(self, task, interact_events):
        interactive_result = task.run(
            task=send_interactive, interact_events=interact_events)
        print(f"The interface counters on {task.host} have been cleared")

    # Here we configure potential interact events. More can be added if needed
    def configure_interact_events(self):
        list_of_responses = []

        if "clear counters" in self.interactive_commands:
            list_of_responses.append(
                ('clear counters', 'Clear "show interface" counters on all interfaces [confirm]', False))
            list_of_responses.append(('yes', '', False))

        return list_of_responses

    # Save the output in the site-stamped & time-stamped directory. Afterwards increment the counter of saved outputs
    def save_output(self, task, result):
        with open(f"/home/kamil/Network_Interface/output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{task.host}.txt", "w") as f:
            f.write(result)
        self.output_counter += 1


if __name__ == '__main__':
    # Required arguments - site, role
    # Optional arguments - platform, commands, interactive_commands, maintenance
    parser = argparse.ArgumentParser(
        description='Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True,
                        help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    parser.add_argument('-p', '--platform', type=str, required=False,
                        help='The platform of the targeted devices (eos/iosxe/iosxr/nxos)')
    parser.add_argument('-c', '--commands', type=str, nargs='+',
                        required=False, help='The commands to be run against the devices')
    parser.add_argument('-ic', '--interactive_commands', type=str, nargs='+',
                        required=False, help='The interactive commands to be run against the devices')
    parser.add_argument('-m', '--maintenance', type=str, required=False,
                        help='Whether this is for a specific maintenance (y). This will use the maintenance config/hosts instead')

    args = parser.parse_args()
    Net_Int = Scrapli_Network_Interface(
        args.site, args.role, args.platform, args.commands, args.interactive_commands, args.maintenance)
    Net_Int.main()
