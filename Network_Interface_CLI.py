from nornir_utils.plugins.functions import print_result
from nornir import InitNornir
from supporting_scripts import get_credentials
from nornir_utils.plugins.tasks.files import write_file
import argparse
from nornir_utils.plugins.functions import print_result
from nornir_napalm.plugins.tasks import napalm_get, napalm_cli
from nornir.core.filter import F

class Network_Interface():

    def __init__(self, site, role, commands):
        self.site = site
        self.role = role
        self.commands = commands
        self.nr = InitNornir(config_file='/home/kamil/Network_Interface/nornir_data/config.yaml')

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]

        if self.site.lower() == "all" and self.role.lower() == "all":
            result = self.nr.run(task=self.send_commands, commands=self.commands)
        elif self.site.lower() == "all":
            target = self.nr.filter(role=self.role)
            result = target.run(task=self.send_commands, commands=self.commands)
        elif self.role.lower() == "all":
            target = self.nr.filter(site=self.site)
            result = target.run(task=self.send_commands, commands=self.commands)
        else:
            target = self.nr.filter(site=self.site, role=self.role)
            result = target.run(task=self.send_commands, commands=self.commands)
        
        



    def send_commands(self, task, commands):
        try:
            result = task.run(task=napalm_cli, commands=commands)
            print_result(result)
        except:
            print("Couldn't send a command with a target")
            
        return result









if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True, help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True, help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    parser.add_argument('-c', '--commands', type=str, nargs='+', required=True, help='The commands to be run against the devices')

    args=parser.parse_args()

    Net_Int = Network_Interface(args.site, args.role, args.commands)
    Net_Int.main()


