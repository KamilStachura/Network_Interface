# from typing import ValuesView
# from colorama import Fore
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
        self.threshold = 500
        self.nr = InitNornir(
            config_file='/home/kamil/Network_Interface/nornir_data/config.yaml')
        self.date = date.today()

    def main(self):
        credentials = get_credentials.get_credentials()
        self.nr.inventory.defaults.username = credentials["username"]
        self.nr.inventory.defaults.password = credentials["password"]
        self.mkdir_today()

        # if self.site.lower() == "all" and self.role.lower() == "all":
        #     result = self.nr.run(task=self.send_command)
        # elif self.site.lower() == "all":
        #     target = self.nr.filter(role=self.role)
        #     result = target.run(task=self.send_command)
        # elif self.role.lower() == "all":
        #     target = self.nr.filter(site=self.site)
        #     result = target.run(task=self.send_command)
        # else:
        #     target = self.nr.filter(site=self.site, role=self.role)
        #     result = target.run(task=self.send_command)

        compare = input(
            "Would you like to compare the old interface errors with the new ones? (y/n) ")
        if compare.lower() == "y":
            # Temp Static date for testing
            old_date = "2021-08-20"
            # old_date = input(
            #     "Provide the date-folder of the old data (yyyy-mm-dd): ")
            old_data = self.retrieve_data(old_date)
            new_data = self.retrieve_data(self.date)
            degraded_interfaces = self.find_degraded_interfaces(
                old_data, new_data)
            degraded_links = self.match_interfaces(
                new_data, degraded_interfaces)

            print(simplejson.dumps(degraded_links, indent=4))
            csv_ready_degraded_links = self.format_degraded_links_to_csv(degraded_links)
            self.save_csv(csv_ready_degraded_links, old_date)


    def mkdir_today(self):
        try:
            os.makedirs(
                f"/home/kamil/Network_Interface/output/{self.site}/{self.date}")
        except OSError:
            pass

    def send_command(self, task):
        result = task.run(task=send_command, command=self.command)
        parsed_output = result.scrapli_response.genie_parse_output()
        formated_output = self.format_output(task, result=parsed_output)
        return formated_output

    def format_output(self, task, result) -> dict:
        formatted_output = {}
        statistics_to_retrieve = ["enabled", "oper_status",
                                  "line_protocol", "description", "mtu", "mac_address", "ipv4"]
        counters_to_retrieve = ["in_pkts", "out_pkts", "in_runts",
                                "in_giants", "in_errors", "in_crc_errors", "out_errors"]
        interfaces_to_ignore = ["Loop", "Vlan", "Port"]

        for interface in result:
            if interface[:4] not in interfaces_to_ignore:
                interface_dict = {}
                for statistic in statistics_to_retrieve:
                    if statistic == "ipv4":
                        try:
                            for key, value in result[interface][statistic].items():
                                interface_dict[statistic] = key
                        except:
                            pass
                    else:
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
        return formatted_output

    def save_output(self, task, formatted_output):
        with open(f"/home/kamil/Network_Interface/output/{self.site}/{self.date}/{task.host}.txt", "w") as f:
            f.write(simplejson.dumps(formatted_output, indent=4))

    def retrieve_data(self, date) -> dict:
        devices_interfaces = {}
        try:
            all_outputs = os.listdir(
                f"output/{self.site}/{date}")
            for output_file in all_outputs:
                with open(f"output/{self.site}/{date}/{output_file}", "r") as f:
                    device_name = output_file.strip(".txt")
                    data = simplejson.loads(f.read())
                    devices_interfaces[device_name] = data
            return devices_interfaces
        except FileNotFoundError:
            print("Old file is missing")

    def find_degraded_interfaces(self, old_data, new_data) -> dict:
        degraded_interfaces = {}
        statistics_to_check = ["in_errors", "in_crc_errors", "out_errors"]
        for device in new_data:
            if device in old_data:
                bad_interfaces = {}
                for interface in new_data[device]:
                    bad_statistics = {}
                    for statistic in statistics_to_check:
                        if int(new_data[device][interface][statistic]) > int(old_data[device][interface][statistic]) and int(new_data[device][interface][statistic]) > int(self.threshold):
                            bad_statistics[statistic] = {
                                "old value": old_data[device][interface][statistic],
                                "new value": new_data[device][interface][statistic]
                            }
                    if bad_statistics:
                        for statistic in statistics_to_check:
                            if statistic not in bad_statistics:
                                bad_statistics[statistic] = {
                                "old value": old_data[device][interface][statistic],
                                "new value": new_data[device][interface][statistic]
                            }
                        bad_interfaces[interface] = bad_statistics
                if bad_interfaces:
                    degraded_interfaces[device] = bad_interfaces
        return degraded_interfaces

    def match_interfaces(self, new_data, degraded_interfaces) -> dict:
        degraded_links = {}
        print(degraded_interfaces)
        for device in list(degraded_interfaces):
            for interface in list(degraded_interfaces[device]):
                interface_found = False
                host_description = new_data[device][interface]["description"]
                description_without_host = host_description[len(device):].strip(" <>")
                peer_name = description_without_host.split(" ")[0]
                expected_peer_description = peer_name + "<>" + device
                sanitized_host_description = device + "<>" + peer_name

                for peer_device in list(degraded_interfaces):
                    if peer_device == device:
                        continue
                    for peer_interface in list(degraded_interfaces[peer_device]):
                        peer_description = new_data[peer_device][peer_interface]["description"]

                        if f"Network Link - {sanitized_host_description}" in degraded_links and interface_found == False:
                            interface_found = True
                            link_dict = {
                                f"{device} ({interface})": new_data[device][interface],
                                f"{peer_device} ({peer_interface})": new_data[peer_device][peer_interface]
                            }

                            for statistic in list(degraded_interfaces[device][interface]):
                                link_dict[f"{device} ({interface})"][f"{statistic}_old"] = degraded_interfaces[device][interface][statistic]["old value"]
                            for statistic in degraded_interfaces[peer_device][peer_interface]:
                                link_dict[f"{peer_device} ({peer_interface})"][f"{statistic}_old"] = degraded_interfaces[peer_device][peer_interface][statistic]["old value"]

                            degraded_links[f"Network Link - {expected_peer_description} - 2nd Link"] = link_dict

                            del degraded_interfaces[peer_device][peer_interface]
                            del degraded_interfaces[device][interface]

                        elif expected_peer_description in peer_description.strip(" ") and expected_peer_description not in degraded_links:
                            interface_found = True
                            link_dict = {
                                f"{device} ({interface})": new_data[device][interface],
                                f"{peer_device} ({peer_interface})": new_data[peer_device][peer_interface]
                            }
                            for statistic in list(degraded_interfaces[device][interface]):
                                link_dict[f"{device} ({interface})"][f"{statistic}_old"] = degraded_interfaces[device][interface][statistic]["old value"]
                            for statistic in degraded_interfaces[peer_device][peer_interface]:
                                link_dict[f"{peer_device} ({peer_interface})"][f"{statistic}_old"] = degraded_interfaces[peer_device][peer_interface][statistic]["old value"]

                            degraded_links[f"Network Link - {sanitized_host_description}"] = link_dict

                            del degraded_interfaces[peer_device][peer_interface]
                            del degraded_interfaces[device][interface]

        for device in degraded_interfaces:
            for interface in degraded_interfaces[device]:
                link_dict = {
                    f"{device} ({interface})": new_data[device][interface]
                }
                for statistic in list(degraded_interfaces[device][interface]):
                    link_dict[f"{device} ({interface})"][f"{statistic}_old"] = degraded_interfaces[device][interface][statistic]["old value"]
                degraded_links["Host Link - " + (new_data[device][interface]["description"])] = link_dict

        return degraded_links


    def format_degraded_links_to_csv(self, degraded_links) -> str:
        formatted_string = ""

        for link in degraded_links:
            if "Network" in link.split(" ")[0]:
                temp_dict = {}
                link_string = ""
                for index, interface in enumerate(degraded_links[link], start=1):
                    temp_dict[f"interface{index}"] = degraded_links[link][interface]
                    temp_dict[f"interface{index}"]["name"] = interface


                link_string = f"""
                {link},,,
                {temp_dict["interface1"]["name"]},,{temp_dict["interface2"]["name"]},
                Operational Status: {temp_dict["interface1"]["oper_status"].upper()},,Operational Status: {temp_dict["interface2"]["oper_status"].upper()}
                Description: {temp_dict["interface1"]["description"]},,Description: {temp_dict["interface2"]["description"]}
                MTU: {temp_dict["interface1"]["mtu"]},,MTU: {temp_dict["interface2"]["mtu"]}
                IPv4 Address: {temp_dict["interface1"]["ipv4"]},,IPv4 Address: {temp_dict["interface2"]["ipv4"]}
                MAC Address: {temp_dict["interface1"]["mac_address"]},,MAC Address: {temp_dict["interface2"]["mac_address"]}
                Input Packets: {temp_dict["interface1"]["in_pkts"]},,Input Packets: {temp_dict["interface2"]["in_pkts"]}
                Output Packets: {temp_dict["interface1"]["out_pkts"]},,Output Packets: {temp_dict["interface2"]["out_pkts"]}
                Input Errors: {temp_dict["interface1"]["in_errors"]},,Input Errors: {temp_dict["interface2"]["in_errors"]}
                Input Errors (Old): {temp_dict["interface1"]["in_errors_old"]},,Input Errors (Old): {temp_dict["interface2"]["in_errors_old"]}
                Input Errors Difference: {int(temp_dict["interface1"]["in_errors"]) - temp_dict["interface1"]["in_errors_old"]},,Input Errors Difference: {int(temp_dict["interface2"]["in_errors"]) - temp_dict["interface2"]["in_errors_old"]}
                Input CRC Errors: {temp_dict["interface1"]["in_crc_errors"]},,Input CRC Errors: {temp_dict["interface2"]["in_crc_errors"]}
                Input CRC Errors (Old): {temp_dict["interface1"]["in_crc_errors_old"]},,Input CRC Errors (Old): {temp_dict["interface2"]["in_crc_errors_old"]}
                Input CRC Errors Difference: {int(temp_dict["interface1"]["in_crc_errors"]) - temp_dict["interface1"]["in_crc_errors_old"]},,Input Errors Difference: {int(temp_dict["interface2"]["in_crc_errors"]) - temp_dict["interface2"]["in_crc_errors_old"]}
                Input Runts: {temp_dict["interface1"]["in_runts"]},,Input Runts: {temp_dict["interface2"]["in_runts"]}
                Input Giants: {temp_dict["interface1"]["in_giants"]},,Input Giants: {temp_dict["interface2"]["in_giants"]}
                Output Errors:{temp_dict["interface1"]["out_errors"]},,Output Errors: {temp_dict["interface2"]["out_errors"]}
                Output Errors (Old):{temp_dict["interface1"]["out_errors_old"]},,Output Errors (Old): {temp_dict["interface2"]["out_errors_old"]}
                Output Errors Difference: {int(temp_dict["interface1"]["out_errors"]) - temp_dict["interface1"]["out_errors_old"]},,Output Errors Difference: {int(temp_dict["interface2"]["out_errors"]) - temp_dict["interface2"]["out_errors_old"]}
                ,,,,
                """
                formatted_string = formatted_string + link_string

            elif "Host" in link.split(" ")[0]:
                for interface in degraded_links[link]:

                    link_string = f"""
                    {link},,,
                    {interface},,,
                    Operational Status: {degraded_links[link][interface]["oper_status"].upper()},,,
                    Description: {degraded_links[link][interface]["description"]},,,
                    MTU: {degraded_links[link][interface]["mtu"]},,,
                    IPv4 Address: {degraded_links[link][interface]["ipv4"]},,,
                    MAC Address:  {degraded_links[link][interface]["mac_address"]},,,
                    Input Packets: {degraded_links[link][interface]["in_pkts"]},,,
                    Output Packets: {degraded_links[link][interface]["out_pkts"]},,,
                    Input Errors: {degraded_links[link][interface]["in_errors"]},,,
                    Input Errors (Old): {degraded_links[link][interface]["in_errors_old"]},,,
                    Input CRC Errors: {degraded_links[link][interface]["in_crc_errors"]},,,
                    Input CRC Errors (Old): {degraded_links[link][interface]["in_crc_errors_old"]},,,
                    Input Runts: {degraded_links[link][interface]["in_runts"]},,,
                    Input Giants: {degraded_links[link][interface]["in_giants"]},,,
                    Output Errors: {degraded_links[link][interface]["out_errors"]},,,
                    Output Errors (Old): {degraded_links[link][interface]["out_errors_old"]},,,
                    ,,,,
                    """
                    formatted_string = formatted_string + link_string.strip(" ")
        return formatted_string


    def save_csv(self, csv_ready_data, old_date):
        with open(f"/home/kamil/Network_Interface/output/{self.site}/Comparison_{self.date}_{old_date}.csv", "w") as f:
            f.write(csv_ready_data)
        return print("The comparison has been saved in: /home/kamil/Network_Interface/output/{self.site}/Comparison_{old_date}_&_{self.date}.csv")




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
