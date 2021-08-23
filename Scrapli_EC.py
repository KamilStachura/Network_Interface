from colorama import Fore
from datetime import date
import simplejson
import os
import argparse
from nornir_utils.plugins.functions import print_result
from nornir import InitNornir
from nornir_scrapli.tasks import send_command
from supporting_scripts import get_credentials


class Scrapli_CRC_Detector():

    def __init__(self, site, role, commands=None):
        self.site = site
        self.role = role
        self.command = "show interfaces"
        self.nr = InitNornir(
            config_file='/home/kamil/Network_Interface/nornir_data/config.yaml')
        self.date = date.today()

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]
        self.mkdir_today()

        if self.site.lower() == "all" and self.role.lower() == "all":
            result = self.nr.run(task=self.send_command)
        elif self.site.lower() == "all":
            target = self.nr.filter(role=self.role)
            result = target.run(task=self.send_command)
        elif self.role.lower() == "all":
            target = self.nr.filter(site=self.site)
            result = target.run(task=self.send_command)
        else:
            target = self.nr.filter(site=self.site, role=self.role)
            result = target.run(task=self.send_command)

        # compare = input(
        #     "Would you like to compare the old interface errors with the new ones? (y/n) ")
        # if compare.lower() == "y":
        #     old_date = input(
        #         "Provide the date-folder of the old data (yyyy-mm-dd): ")
        #     old_data = self.retrieve_data(old_date)
        #     new_data = self.retrieve_data(self.date)
        #     difference = self.compare_data(old_data, new_data)
        #     self.display_data(difference)

    # def display_data(self, difference):
    #     for device in difference:
    #         print("Affected Device: " + Fore.GREEN + device)
    #         for interface in difference[device]:
    #             print("Affected Interface: " + Fore.GREEN + interface)
    #             for statistics in difference[device][interface]:
    #                 print(statistics)
    #             print("\n")

    # def compare_data(self, old_data, new_data):
    #     Faults_report = {}
    #     statistics_to_check = ["rx_discards",
    #                            "rx_errors", "tx_discards", "tx_errors"]
    #     for device in new_data:
    #         if device in old_data:
    #             bad_interfaces = {}
    #             for interface in new_data[device]:
    #                 bad_statistics = []
    #                 for statistic, value in new_data[device][interface].items():
    #                     if int(new_data[device][interface][statistic]) > int(old_data[device][interface][statistic]) and statistic in statistics_to_check:
    #                         bad_statistics.append(
    #                             f"{statistic} - Old value: {old_data[device][interface][statistic]}, New value: {value}")
    #                 if bad_statistics:
    #                     bad_interfaces[interface] = bad_statistics
    #             if bad_interfaces:
    #                 Faults_report[device] = bad_interfaces
    #     return(Faults_report)

    def mkdir_today(self):
        try:
            os.makedirs(f"/home/kamil/Network_Interface/output/{self.date}")
        except OSError:
            pass

    def save_output(self, task, formatted_output):
        with open(f"/home/kamil/Network_Interface/output/{self.date}/{task.host}.txt", "w") as f:
            f.write(simplejson.dumps(formatted_output, indent=4))

    def format_output(self, task, result):
        formatted_output = {}
        statistics_to_retrieve = ["enabled", "oper_status",
                                  "line_protocol", "description", "mtu", "mac_address", "ipv4"]
        counters_to_retrieve = ["in_pkts", "out_pkts", "in_runts",
                                "in_giants", "in_errors", "in_crc_errors", "out_errors"]
        interfaces_to_ignore = ["Loop", "Vlan", "Port"]

### CHECK WHAT OTHER ERRORS CAN BE CAUGHT ### 

        for interface in result:
            if interface[:4] not in interfaces_to_ignore:
                interface_dict = {}
                for statistic in statistics_to_retrieve:
                    try:
                        interface_dict[statistic] = result[interface].get(
                            statistic)
                    except:
                        pass
                for counter in counters_to_retrieve:
                    try:
                        interface_dict[counter] = result[interface]["counters"].get(
                            counter)
                    except:
                        pass
            formatted_output[interface] = interface_dict
        self.save_output(task, formatted_output)

    def send_command(self, task):
        result = task.run(task=send_command, command=self.command)
        parsed_output = result.scrapli_response.genie_parse_output()
        self.format_output(task, result=parsed_output)

    # def retrieve_data(self, date):
    #     devices_interfaces = {}
    #     try:
    #         all_outputs = os.listdir(
    #             f"/home/kamil/Network_Interface/output/{date}")
    #         for output_file in all_outputs:
    #             with open(f"/home/kamil/Network_Interface/output/{date}/{output_file}", "r") as f:
    #                 device_name = output_file.strip(".txt")
    #                 interfaces_dict = {}
    #                 data = simplejson.loads(f.read())
    #                 for interface in list(data["get_interfaces_counters"]):
    #                     interfaces_dict[interface] = data["get_interfaces_counters"][interface]

    #                 devices_interfaces[device_name] = interfaces_dict
    #         return devices_interfaces
    #     except FileNotFoundError:
    #         print("Old file is missing")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provide options to the Network Interface')
    parser.add_argument('-s', '--site', type=str, required=True,
                        help='The targeted site to run the commands against')
    parser.add_argument('-r', '--role', type=str, required=True,
                        help='The role of targeted devices (SPINE/LEAF/TRDSW/...)')

    args = parser.parse_args()
    Scrapli_EC = Scrapli_CRC_Detector(args.site, args.role)
    Scrapli_EC.main()
