from EVE_NG.provisioning import (
    login,
    create_lab,
    test_add_config,
    start_nodes,
    logout,
    create_node,
    get_nodes,
    create_net,
    connect_intf,
    device_connect,
)
from EVE_NG.devices import Router
import time
import sys
from threading import Thread
import os
from EVE_NG.resources import connect_to_api
from render_templates import render_template
from ipaddress import IPv4Interface

try:
	ProjectBase = sys.argv[1]
except IndexError:
	raise Exception("You need to specify a lab name!")
ProjectName = "{}".format("%20".join(ProjectBase.split()))
my_devices = connect_to_api("GET", "http://127.0.0.1:5005/api/v1/devices/")
my_devices = my_devices.json().get("data")
number_of_nodes = len(my_devices)
print("********** Rendering Templates... **********")
for device in my_devices:
	if device["NOS"] == "IOS":
		mgmt_ip = f"{device['Management IP'].split('/')[0]} {IPv4Interface(device['Management IP']).with_netmask.split('/')[1]}"
	render_template(device["deviceName"], "initial", NOS=device["NOS"], mgmt_ip=mgmt_ip)
time_before = time.time()
cookies = login()
create_lab(cookies, ProjectBase)
base_left = 20
base_top = 50

print("********** Deploying Cloud Connection... **********")
create_net(cookies, ProjectName)
print("********** Phase: Deploying Nodes... **********")
for i in range(0, number_of_nodes):
	node_id = i + 1
	hostname = f"R{node_id}"
	filepath = os.path.exists(f"./renderedTemplates/deployment/{hostname}.txt")
	if not filepath:
		print(f"{hostname} has no configuration file! Skipping...")
		continue
	router = Router(hostname, left=base_left, top=base_top).to_json()
	create_node(cookies, router, ProjectName)
	connect_intf(cookies, ProjectName, node_id)
	time.sleep(0.1)
	with open(f"./renderedTemplates/deployment/{hostname}.txt", "r") as configfile:
		config = {"data": configfile.read()}
		test_add_config(cookies, config, ProjectName, node_id)
	base_left += 40
	base_top += 50

print("********** Phase: Starting Nodes... **********")
start_nodes(cookies, ProjectName)
address_info = get_nodes(cookies, ProjectName)
logout(cookies)
mgmt_info = [
    (value["name"], value["url"]) for key, value in address_info.get("data").items()
]

print("********** Finalizing Provisioning... **********")
time.sleep(2)
threads = []
for x, device in enumerate(mgmt_info, 1):
	# print(((device[1]).split(":")[1])[2:], (device[1]).split(":")[-1])
	keywords = {"auth": False}
	args = [(device[1]).split(":")[1][2:], int((device[1]).split(":")[-1]), "no\n\n"]
	th = Thread(target=device_connect, args=args, kwargs=keywords)
	th.start()
	threads.append(th)
for th in threads:
	th.join()
print("********** Done! **********")
time_after = time.time()
print(
    "********** Total Time: {} seconds **********".format(
        round(time_after - time_before, 2)
    )
)
