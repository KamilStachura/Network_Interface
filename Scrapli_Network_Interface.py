from supporting_scripts import get_credentials
from nornir_scrapli.tasks import send_commands, send_interactive
from nornir import InitNornir
from datetime import datetime
import argparse
import os


class Scrapli_Network_Interface():

    def __init__(self, site, role, commands=None, interactive_commands=None):
        self.site = site
        self.role = role
        self.commands = commands
        self.interactive_commands = interactive_commands
        self.nr = InitNornir(config_file='nornir_data/config.yaml')
        self.date = datetime.now()

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]
        self.mkdir_today()
        if self.interactive_commands:
            interact_events = self.configure_interact_events()

        if self.site.lower() == "all" and self.role.lower() == "all":
            if self.commands:
                result = self.nr.run(task=self.send_commands)
            if self.interactive_commands:
                interactive_result = self.nr.run(task=self.send_interactive_commands, interact_events=interact_events)
        elif self.site.lower() == "all":
            target = self.nr.filter(role=self.role)
            if self.commands:
                result = target.run(task=self.send_commands)
            if self.interactive_commands:
                interactive_result = target.run(task=self.send_interactive_commands, interact_events=interact_events)
        elif self.role.lower() == "all":
            target = self.nr.filter(site=self.site)
            if self.commands:
                result = target.run(task=self.send_commands)
            if self.interactive_commands:
                interactive_result = target.run(task=self.send_interactive_commands, interact_events=interact_events)
        else:
            target = self.nr.filter(site=self.site, role=self.role)
            if self.commands:
                result = target.run(task=self.send_commands)
            if self.interactive_commands:
                interactive_result = target.run(task=self.send_interactive_commands, interact_events=interact_events)

        print(f"Commands sent: {self.commands}\n")
        print(f"Interactive Commands sent: {self.interactive_commands}\n")
        print(f"The output can be found in: output/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}")



    def mkdir_today(self) -> "Directory":
        try:
            os.makedirs(
                f"/home/kamil/Network_Interface/output/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}")
        except OSError:
            pass

    def send_commands(self, task):
        result = task.run(task=send_commands, commands=self.commands)
        self.save_output(task, result=result.result)


    def send_interactive_commands(self, task, interact_events):
        interactive_result = task.run(task=send_interactive, interact_events=interact_events)
        print(f"The interface counters on {task.host} have been cleared")

    # Here we configure potential interact events
    def configure_interact_events(self):
        list_of_responses = []

        if "clear counters" in self.interactive_commands:
            list_of_responses.append(('clear counters', 'Clear "show interface" counters on all interfaces [confirm]', False))
            list_of_responses.append(('yes', '', False))

        return list_of_responses


    def save_output(self, task, result):
        with open(f"/home/kamil/Network_Interface/output/{self.site}/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{task.host}.txt", "w") as f:
            f.write(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True,
                        help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    parser.add_argument('-c', '--commands', type=str, nargs='+',
                        required=False, help='The commands to be run against the devices')
    parser.add_argument('-ic', '--interactive_commands', type=str, nargs='+',
                        required=False, help='The interactive commands to be run against the devices')
                    

    args = parser.parse_args()
    Net_Int = Scrapli_Network_Interface(args.site, args.role, args.commands, args.interactive_commands)
    Net_Int.main()
