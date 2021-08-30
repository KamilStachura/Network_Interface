from nornir import InitNornir
from supporting_scripts import get_credentials
from nornir_utils.plugins.functions import print_result
from nornir_napalm.plugins.tasks import napalm_get
import argparse
import os
import simplejson
from datetime import date
from colorama import Fore

class Network_Interface():

    def __init__(self, site, role, commands=None):
        self.site = site
        self.role = role
        self.commands = "get_interfaces_counters"
        self.nr = InitNornir(config_file='/home/kamil/Network_Interface/nornir_data/config.yaml')
        self.date = date.today()

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]
        self.mkdir_today()
        
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
        
        print_result(result)

        compare = input("Would you like to compare the old interface errors with the new ones? (y/n) ")
        if compare.lower() == "y":
            old_date = input("Provide the date-folder of the old data (yyyy-mm-dd): ")
            old_data = self.retrieve_data(old_date)
            new_data = self.retrieve_data(self.date)
            difference = self.compare_data(old_data, new_data)
            self.display_data(difference)


    def display_data(self, difference):
        for device in difference:
            print("Affected Device: " + Fore.GREEN + device)
            for interface in difference[device]:
                print("Affected Interface: " + Fore.GREEN + interface)
                for statistics in difference[device][interface]:
                    print(statistics)
                print("\n")



    def compare_data(self, old_data, new_data):
        Faults_report = {}
        statistics_to_check = ["rx_discards", "rx_errors", "tx_discards", "tx_errors"]
        for device in new_data:
            if device in old_data:
                bad_interfaces = {}
                for interface in new_data[device]:
                    bad_statistics = []
                    for statistic, value in new_data[device][interface].items():
                        if int(new_data[device][interface][statistic]) > int(old_data[device][interface][statistic]) and statistic in statistics_to_check:
                            bad_statistics.append(f"{statistic} - Old value: {old_data[device][interface][statistic]}, New value: {value}")
                    if bad_statistics:
                        bad_interfaces[interface] = bad_statistics
                if bad_interfaces:
                    Faults_report[device] = bad_interfaces
        return(Faults_report)


    def mkdir_today(self):
        try:
            os.makedirs(f"/home/kamil/Network_Interface/output/{self.date}")
        except OSError:
            pass


    def save_output(self, task, result):
        with open(f"/home/kamil/Network_Interface/output/{self.date}/{task.host}.txt", "w") as f:
            f.write(simplejson.dumps(result, indent=4))


    def send_commands(self, task, commands):
        result = task.run(task=napalm_get, getters=commands)
        self.save_output(task, result.result)


    def retrieve_data(self, date):
        devices_interfaces = {}
        try:
            all_outputs = os.listdir(f"/home/kamil/Network_Interface/output/{date}")
            for output_file in all_outputs:
                with open(f"/home/kamil/Network_Interface/output/{date}/{output_file}", "r") as f:
                    device_name = output_file.strip(".txt")
                    interfaces_dict = {}
                    data = simplejson.loads(f.read())
                    for interface in list(data["get_interfaces_counters"]):
                        interfaces_dict[interface] =  data["get_interfaces_counters"][interface]

                    devices_interfaces[device_name] = interfaces_dict
            return devices_interfaces
        except FileNotFoundError:
            print("Old file is missing")
            
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True, help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True, help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')
    # parser.add_argument('-c', '--commands', type=str, nargs='+', required=True, help='The commands to be run against the devices')

    args=parser.parse_args()

    Net_Int = Network_Interface(args.site, args.role)
    Net_Int.main()


