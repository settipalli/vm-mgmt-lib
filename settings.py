#!/usr/bin/env python

# ==============================================================================
# Name          :   settings.py
#
# Description   :   Common settings to be used by VM management library.
#
# Version       :   1.0.0
#
# Author        :   Santhoshkumar Settipalli
#
# Change log    :
#   25-Dec-2013 :    Santhoshkumar Settipalli (santhosh.settipalli@gmail.com)
#                    Initial version.
#
# ==============================================================================

DISK_20GB = 20971520  # In KB (20 GB).
DISK_40GB = 41943040  # In KB.
DISK_100GB = 104857600  # In KB.

RAM_2GB = 2048  # In MB.
RAM_4GB = 4096  # In MB.
RAM_8GB = 8192  # In MB.
RAM_16GB = 16384  # In MB.

VIRTUAL_CPU_2NOS = 2
VIRTUAL_CPU_4NOS = 4
VIRTUAL_CPU_8NOS = 8
VIRTUAL_CPU_16NOS = 16

# Location of the log file to log user actions.
LOG_FOLDER = "/var/log/vm_mgmt_lib"
LOG_FILE = LOG_FOLDER + "/vm_mgmt_lib.log"
LOG_LEVEL = "debug" # Supported value: 'debug', 'info', 'warning', 'error', 'critical'

# Location to save the IP address of the deployed VM.
DEPLOYED_VM_IP_SAVE_FOLDER="/tmp"

try:
    from collections import namedtuple
    vm_type = namedtuple("vm_type", ["name", "hostname", "datastore", "ram", "cpus", "disksize"])
except:
    class vm_type(object):
        def __init__(self, name, hostname, datastore, ram, cpus, disksize):
            self.name = name
            self.hostname = hostname
            self.datastore = datastore
            self.ram = ram
            self.cpus = cpus
            self.disksize = disksize

try:
    vcenter_type = namedtuple("vcenter_type", ["ip", "username", "password", "datacenter", "datastore", "hostname", "template"])
except:
    class vcenter_type(object):
        def __init__(self, ip, username, password, datacenter, datastore, hostname, template):
            self.ip = ip
            self.username = username
            self.password = password

            self.datacenter = datacenter
            self.datastore = datastore
            self.hostname = hostname
            self.template = template

try:
    supported_actions = namedtuple("supported_actions", ["action"])
except:
    class supported_actions(object):
        def __init__(self, action):
            self.action = action

try:
    vm_login_info = namedtuple("vm_login_info", ["username", "password"])
except:
    class vm_login_info(object):
        def __init__(self, username, password):
            self.username = username
            self.password = password

try:
    vm_network_adapter = namedtuple("vm_network_adapter", ["adapter_name"])
except:
    class vm_network_adapter(object):
        def __init__(self, adapter_name):
            self.adapter_name = adapter_name


VM_TYPES = {
    # Add VM types here. Eg.
    # "VM_Key" : vm_type("My VM Name", "vm-hostname", "datastore", RAM_8GB, VIRTUAL_CPU_8NOS, DISK_100GB),
}

VCENTER_SERVERS = {
    # Add vCenter(s) details here. E.g.
    # "Key": vcenter_type('vcenter-ip', "root", "<password>", "Data-Center", "Data-Store", "exsi-hostname-connected-to-this-vcenter", "template-to-be-used-to-create-a-vm-clone"),    
}

SUPPORTED_ACTIONS = {
    "create-vm" : "create_vm",
    "delete-vm" : "delete_vm",
    "remove-cd-device-from-vm" : "remove_cd",
}

GUEST_LOGIN_INFO = {
    # Add login credentials that could be used to login to the Guest.
    # The 'VM-Key' should match the VM-Key used for VMs defined under VM_TYPES.
    # "VM-Key": vm_login_info("root", "password"),
}

NETWORK_ADAPTER = {
    "E1000": vm_network_adapter("E1000"),
    "VMXNET2": vm_network_adapter("VMXNET2"),
    "VMXNET3": vm_network_adapter("VMXNET3"),
}

