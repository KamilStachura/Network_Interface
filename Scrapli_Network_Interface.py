from supporting_scripts import get_credentials
from nornir_scrapli.tasks import send_commands
from nornir import InitNornir
from datetime import datetime
import argparse
import os


class Scrapli_Network_Interface():

    def __init__(self, site, role, commands):
        self.site = site
        self.role = role
        self.commands = commands
        self.nr = InitNornir(config_file='nornir_data/config.yaml')
        self.date = datetime.now()

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]
        self.mkdir_today()

        if self.site.lower() == "all" and self.role.lower() == "all":
            result = self.nr.run(task=self.send_commands)
        elif self.site.lower() == "all":
            target = self.nr.filter(role=self.role)
            result = target.run(task=self.send_commands)
        elif self.role.lower() == "all":
            target = self.nr.filter(site=self.site)
            result = target.run(task=self.send_commands)
        else:
            target = self.nr.filter(site=self.site, role=self.role)
            result = target.run(task=self.send_commands)

        print(f"The following commands have been sent: {self.commands}\n")
        print(f"The output can be found in: output/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}")

    def mkdir_today(self) -> "Directory":
        try:
            os.makedirs(
                f"/home/kamil/Network_Interface/output/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}")
        except OSError:
            pass

    def send_commands(self, task) -> "Result":
        result = task.run(task=send_commands, commands=self.commands)
        self.save_output(task, result=result.result)

    def save_output(self, task, result) -> "File":
        with open(f"/home/kamil/Network_Interface/output/{self.date.day}-{self.date.month}-{self.date.year}_{self.date.hour}-{self.date.minute}/{self.site}/{task.host}.txt", "w") as f:
            f.write(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True,
                        help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    parser.add_argument('-c', '--commands', type=str, nargs='+',
                        required=True, help='The commands to be run against the devices')

    args = parser.parse_args()
    Net_Int = Scrapli_Network_Interface(args.site, args.role, args.commands)
    Net_Int.main()
