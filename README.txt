A network interface for executing ad-hoc show commands across groups of devices based on platform, role, site, their combination, or a list of devices.
The ouput is saved in a site- & time-stamped directory within the output folder.
This script leverages Nornir for inventory framework and multi-threading, and Scrapli as the connection manager.

How to Use:
1. Define your hosts file - This is your network devices' inventory
2. Execute the script by providing the following arguments:
    Requred arguments - site (-s) & role (-r) OR devices (-d), commands (-c), primary_user (-pu)
    Optional arguments - platform (-p), backup_user (-bu), maintenance (-m)

Example 1 - Execute "show run" & "show ver" against all LEAFs (role) in WARSAW (site)
$python network_interface.py -s WARSAW -r LEAF -c "show run" "show ver" -pu <username>

Example 2 - Execute "show run" & "show ver" against all SPINEs (role) in all sites running Arista eos
$python network_interface.py -s ALL -r SPINE -p eos -c "show run" "show ver" -pu <username>

Example 3 - Execute "show run" & "show ver" against all devices in XYZ site running nxos
with backup credentials in case some devices may not work with the primary credentials
$python network_interface.py -s XYZ -r ALL -p nxos -c "show run" "show ver" -pu <primary_username> -bu <backup_username>
