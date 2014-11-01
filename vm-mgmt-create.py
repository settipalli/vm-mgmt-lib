#!/usr/bin/env python

# ==============================================================================
# Name          :   vm-mgmt-create.py
#
# Description   :   Common library to create and manipulate VMs.
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

import re
import sys
import settings
from optparse import OptionParser
from pysphere import VIServer, VIProperty
from pysphere.resources import VimService_services as VI
from pysphere.vi_task import VITask


def options():
    parser = OptionParser()
    parser.add_option("--type", dest="type", choices=settings.VM_TYPES.keys(
    ), help="Type of the VM. This has some defaults (name, hostname, datastore) which can be overridden with the other options. Supported choices: " + str(settings.VM_TYPES.keys()))
    parser.add_option(
        "--vcenter", dest="vcenter", type="choice", choices=settings.VCENTER_SERVERS.keys(), help="Choose a vCenter configuration. Supported choices: " + str(settings.VCENTER_SERVERS.keys()))
    parser.add_option("--disksize", dest="disksize", default="41943040", help="Disk size for VM (in KB.). Default=40GB.")
    parser.add_option("--mac", dest="mac", default=None, help="MAC address to use - for example in the case of a rebuild.")
    parser.add_option("--name", dest="name", help="Name for this VM.")
    parser.add_option("--notes", dest="notes", help="Description of this VM.")
    parser.add_option("--hostname", dest="hostname", help="Hostname for this VM.")
    parser.add_option("--domain", dest="domain", default="my-local-domain.local", help="Domain for this VM.")
    parser.add_option("--ram", dest="ram", type="int", help="RAM size for this VM.")
    parser.add_option("--cpus", dest="cpus", type="int", help="Number of CPUs for this VM.")
    parser.add_option("--datastore", dest="datastore",
                      help="Datastore to use for this VM (a substring can be supplied, the first match will be used.)")
    parser.add_option("--iso", dest="iso",
                      help="ISO file path relateive to Datastore.")
    parser.add_option("-t", "--test", dest="test", default=False, action="store_true", help="Test")
    parser.add_option("--user", dest="user", help="Username to connect to ESX Server.")
    parser.add_option("--pass", dest="passwd", help="Password to connect to ESX Server.")
    parser.add_option("--esx-host", dest="esx_host", help="Hostname of ESX Server to connect to.")
    parser.add_option("--network-adapter", dest="vm_network_adapter", help="Name of the Network interface to which the VM has to be connected to. Supported choices: " +
                      str(settings.NETWORK_ADAPTER.keys()))
    parser.add_option("--datacentername", dest="datacentername", help="Name of the datacenter.")
    parser.add_option("--template", dest="template", help="Name of the template.")

    opts, args = parser.parse_args()

    vcenter_present = opts.vcenter and opts.vcenter in settings.VCENTER_SERVERS
    if vcenter_present:
        vcenter = settings.VCENTER_SERVERS[opts.vcenter]
        opts.esx_host = vcenter.ip
        opts.user = vcenter.username
        opts.passwd = vcenter.password
        opts.datacenter = vcenter.datacenter
        opts.datastore = vcenter.datastore
        opts.esx_hostname = vcenter.hostname
        opts.template = vcenter.template
    else:
        print
        print "ERROR: no support for a deployment where a vCenter or ESXi host server is not available."
        print
        sys.exit(1)

    type_present = opts.type and opts.type in settings.VM_TYPES
    if type_present:
        vmtype = settings.VM_TYPES[opts.type]
        opts.name = opts.name or vmtype.name
        opts.hostname = opts.hostname or vmtype.hostname
        opts.datastore = opts.datastore or vmtype.datastore
        opts.ram = opts.ram or vmtype.ram
        opts.cpus = opts.cpus or vmtype.cpus
        opts.disksize = opts.disksize or vmtype.disksize

    if not opts.vm_network_adapter:
        opts.vm_network_adapter = "VMXNET3"

    opts.ram = opts.ram or 4096
    opts.cpus = opts.cpus or 2

    if not opts.iso:
        print "Cannot continue without ISO path. Use --iso <iso-path-relative-to-datastore>."
        sys.exit(1)

    #    if not opts.name:
    #        print "Choose a name for this VM: ",
    #        opts.name = raw_input().strip()
    #    if not opts.notes:
    #        print "Set the description for this VM: ",
    #        opts.notes = raw_input().strip()
    #    if opts.mac is None:
    #        print "Input a MAC Address if this is a rebuild: "
    #        opts.mac = raw_input().strip()

    # print "Identified options:", opts
    return opts


def connect_vm_cdroms(vm, server):
    connected_cdroms = []
    for dev in vm.properties.config.hardware.device:
        if dev._type == "VirtualCdrom":
        # and dev.connectable.connected:
        # if dev._type == "VirtualCdrom" and dev.connectable.startConnected:
            d = dev._obj
            d.Connectable.set_element_connected(True)
            d.Connectable.set_element_startConnected(True)
            connected_cdroms.append(d)

    if not connected_cdroms:
        print "%s: has no connected cd roms" % vm.properties.name
        return

    request = VI.ReconfigVM_TaskRequestMsg()
    _this = request.new__this(vm._mor)
    _this.set_attribute_type(vm._mor.get_attribute_type())
    request.set_element__this(_this)
    spec = request.new_spec()
    dev_changes = []

    for dev in connected_cdroms:
        dev_change = spec.new_deviceChange()
        dev_change.set_element_device(dev)
        dev_change.set_element_operation("edit")
        dev_changes.append(dev_change)

    spec.set_element_deviceChange(dev_changes)
    request.set_element_spec(spec)
    ret = server._proxy.ReconfigVM_Task(request)._returnval
    # Wait for the task to finish
    # Remove all this section if you don't wish to wait for the task to finish
    task = VITask(ret, server)
    status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
    if status == task.STATE_SUCCESS:
        print "%s: successfully reconfigured" % vm.properties.name
    elif status == task.STATE_ERROR:
        print "%s: Error reconfiguring vm" % vm.properties.name


def change_cdrom_type(dev, dev_type, value=""):
    if dev_type == "ISO":
        iso = VI.ns0.VirtualCdromIsoBackingInfo_Def("iso").pyclass()
        iso.set_element_fileName(value)
        dev.set_element_backing(iso)
    elif dev_type == "HOST DEVICE":
        host = VI.ns0.VirtualCdromAtapiBackingInfo_Def("host").pyclass()
        host.set_element_deviceName(value)
        dev.set_element_backing(host)
    elif dev_type == "CLIENT DEVICE":
        client = VI.ns0.VirtualCdromRemoteAtapiBackingInfo_Def("client").pyclass()
        client.set_element_deviceName("")
        dev.set_element_backing(client)


def get_valid_host_devices(vm):
    env_browser = vm.properties.environmentBrowser._obj
    request = VI.QueryConfigTargetRequestMsg()
    _this = request.new__this(env_browser)
    _this.set_attribute_type(env_browser.get_attribute_type())
    request.set_element__this(_this)
    ret = server._proxy.QueryConfigTarget(request)._returnval
    return [cd.Name for cd in ret.CdRom]


def apply_changes(vm, server, cdrom):
    request = VI.ReconfigVM_TaskRequestMsg()
    _this = request.new__this(vm._mor)
    _this.set_attribute_type(vm._mor.get_attribute_type())
    request.set_element__this(_this)
    spec = request.new_spec()
    dev_change = spec.new_deviceChange()
    dev_change.set_element_device(cdrom)
    dev_change.set_element_operation("edit")
    spec.set_element_deviceChange([dev_change])
    request.set_element_spec(spec)
    ret = server._proxy.ReconfigVM_Task(request)._returnval
    task = VITask(ret, server)
    status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
    if status == task.STATE_SUCCESS:
        print "%s: successfully reconfigured" % vm.properties.name
    elif status == task.STATE_ERROR:
        print "%s: Error reconfiguring vm" % vm.properties.name


def create_vm():
    opts = options()

    # CONNECTION PARAMTERS
    server = opts.esx_host
    user = opts.user
    password = opts.passwd

    # REQUIRED PARAMETERS
    vmname = opts.name
    # datacentername = "ha-datacenter"
    datacentername = opts.datacenter
    hostname = opts.hostname
    annotation = "My Product Product Virtual Machine"
    memorysize = opts.ram
    cpucount = opts.cpus
    # cd_iso_location =
    # "iso/My_Product_2013_02_26_05_15_00.iso"
    # # located in the ESX datastore
    cd_iso_location = opts.iso
    guestosid = "centos64Guest"
    # find your os in
    # http://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/vim.vm.GuestOsDescriptor.GuestOsIdentifier.html
    disksize = (1024 ** 2) * 100  # In Kb: 1024 ** 2 (power) = 1GB; 1GB * 100 = 100GB.

    # OPTIONAL PARAMETERS

    datastorename = opts.datastore  # if None, will use the first datastore available

    # CONNECT TO THE SERVER
    s = VIServer()
    s.connect(server, user, password)

    # GET INITIAL PROPERTIES AND OBJECTS

     # get datacenter
    dcmor = s._get_datacenters()[datacentername]
    dcprops = VIProperty(s, dcmor)
     # get host folder
    hfmor = dcprops.hostFolder._obj

     # get computer resources
    crmors = s._retrieve_properties_traversal(property_names=['name',
                                                              'host'], from_node=hfmor, obj_type='ComputeResource')

     # get host
    for hosts in s.get_hosts().items():
        try:
            if hosts.index(hostname) == 1:
                hostmor = hosts[0]
        except:
            pass

    # get computer resource of this host
    crmor = None
    for cr in crmors:
        if crmor:
            break
        for p in cr.PropSet:
            # print 'p.Name:', p.Name
            if p.Name == "host":
                for h in p.Val.get_element_ManagedObjectReference():
                    if h == hostmor:
                        crmor = cr.Obj
                        break
                if crmor:
                    break
    crprops = VIProperty(s, crmor)

     # get resource pool
    rpmor = crprops.resourcePool._obj

     # get vmFolder
    vmfmor = dcprops.vmFolder._obj

    # CREATE VM CONFIGURATION

     # get config target
    request = VI.QueryConfigTargetRequestMsg()
    _this = request.new__this(crprops.environmentBrowser._obj)
    _this.set_attribute_type(crprops.environmentBrowser._obj.get_attribute_type())
    request.set_element__this(_this)
    h = request.new_host(hostmor)
    h.set_attribute_type(hostmor.get_attribute_type())
    request.set_element_host(h)
    config_target = s._proxy.QueryConfigTarget(request)._returnval

     # get default devices
    request = VI.QueryConfigOptionRequestMsg()
    _this = request.new__this(crprops.environmentBrowser._obj)
    _this.set_attribute_type(crprops.environmentBrowser._obj.get_attribute_type())
    request.set_element__this(_this)
    h = request.new_host(hostmor)
    h.set_attribute_type(hostmor.get_attribute_type())
    request.set_element_host(h)
    config_option = s._proxy.QueryConfigOption(request)._returnval
    defaul_devs = config_option.DefaultDevice

    # get network name
    # would be assigned to the last known working network interface.
    # in this case, it would be VM Network 2.
    network_name = None
    for n in config_target.Network:
        if n.Network.Accessible:
            network_name = n.Network.Name

    # can hard-code it as 'VM Network'

    # get datastore
    # Just verifies that the datastorename mentioned at the top matches with the
    # available list of datastores.
    ds = None
    for d in config_target.Datastore:
        if d.Datastore.Accessible and (datastorename and d.Datastore.Name
                                       == datastorename) or (not datastorename):
            ds = d.Datastore.Datastore
            datastorename = d.Datastore.Name
            break
    if not ds:
        raise Exception("couldn't find datastore")
    volume_name = "[%s]" % datastorename

     # add parameters to the create vm task
    create_vm_request = VI.CreateVM_TaskRequestMsg()
    config = create_vm_request.new_config()
    vmfiles = config.new_files()
    vmfiles.set_element_vmPathName(volume_name)
    config.set_element_files(vmfiles)
    config.set_element_name(vmname)
    config.set_element_annotation(annotation)
    config.set_element_memoryMB(memorysize)
    config.set_element_numCPUs(cpucount)
    config.set_element_guestId(guestosid)
    devices = []

     # add a scsi controller
    disk_ctrl_key = 1
    scsi_ctrl_spec = config.new_deviceChange()
    scsi_ctrl_spec.set_element_operation('add')
    scsi_ctrl = VI.ns0.VirtualLsiLogicController_Def("scsi_ctrl").pyclass()
    scsi_ctrl.set_element_busNumber(0)
    scsi_ctrl.set_element_key(disk_ctrl_key)
    scsi_ctrl.set_element_sharedBus("noSharing")

    scsi_ctrl_spec.set_element_device(scsi_ctrl)
    devices.append(scsi_ctrl_spec)

     # find ide controller
    ide_ctlr = None
    for dev in defaul_devs:
        if dev.typecode.type[1] == "VirtualIDEController":
            ide_ctlr = dev

     # add a cdrom based on a physical device
    if ide_ctlr:
        cd_spec = config.new_deviceChange()
        cd_spec.set_element_operation('add')
        cd_ctrl = VI.ns0.VirtualCdrom_Def("cd_ctrl").pyclass()
        cd_device_backing = VI.ns0.VirtualCdromIsoBackingInfo_Def("cd_device_backing").pyclass()
        ds_ref = cd_device_backing.new_datastore(ds)
        ds_ref.set_attribute_type(ds.get_attribute_type())
        cd_device_backing.set_element_datastore(ds_ref)
        cd_device_backing.set_element_fileName("%s %s" % (volume_name,
                                                          cd_iso_location))
        cd_ctrl.set_element_backing(cd_device_backing)
        cd_ctrl.set_element_key(20)
        cd_ctrl.set_element_controllerKey(ide_ctlr.get_element_key())
        cd_ctrl.set_element_unitNumber(0)
        cd_spec.set_element_device(cd_ctrl)
        devices.append(cd_spec)

     # create a new disk - file based - for the vm
    disk_spec = config.new_deviceChange()
    disk_spec.set_element_fileOperation("create")
    disk_spec.set_element_operation("add")
    disk_ctlr = VI.ns0.VirtualDisk_Def("disk_ctlr").pyclass()
    disk_backing = VI.ns0.VirtualDiskFlatVer2BackingInfo_Def("disk_backing").pyclass()
    disk_backing.set_element_fileName(volume_name)
    disk_backing.set_element_diskMode("persistent")
    disk_backing.ThinProvisioned = True
    disk_ctlr.set_element_key(0)
    disk_ctlr.set_element_controllerKey(disk_ctrl_key)
    disk_ctlr.set_element_unitNumber(0)
    disk_ctlr.set_element_backing(disk_backing)
    disk_ctlr.set_element_capacityInKB(disksize)
    disk_spec.set_element_device(disk_ctlr)
    devices.append(disk_spec)

     # add a NIC. the network Name must be set as the device name to create the NIC.
    nic_spec = config.new_deviceChange()
    if network_name:
        nic_spec.set_element_operation("add")
        nic_ctlr = VI.ns0.VirtualPCNet32_Def("nic_ctlr").pyclass()
        nic_backing = VI.ns0.VirtualEthernetCardNetworkBackingInfo_Def("nic_backing").pyclass()
        nic_backing.set_element_deviceName(network_name)
        nic_ctlr.set_element_addressType("generated")
        nic_ctlr.set_element_backing(nic_backing)
        nic_ctlr.set_element_key(4)
        nic_spec.set_element_device(nic_ctlr)
        devices.append(nic_spec)

    config.set_element_deviceChange(devices)
    create_vm_request.set_element_config(config)
    folder_mor = create_vm_request.new__this(vmfmor)
    folder_mor.set_attribute_type(vmfmor.get_attribute_type())
    create_vm_request.set_element__this(folder_mor)
    rp_mor = create_vm_request.new_pool(rpmor)
    rp_mor.set_attribute_type(rpmor.get_attribute_type())
    create_vm_request.set_element_pool(rp_mor)
    host_mor = create_vm_request.new_host(hostmor)
    host_mor.set_attribute_type(hostmor.get_attribute_type())
    create_vm_request.set_element_host(host_mor)

    # CREATE THE VM
    taskmor = s._proxy.CreateVM_Task(create_vm_request)._returnval
    task = VITask(taskmor, s)
    task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])

    if task.get_state() == task.STATE_ERROR:
        raise Exception("Error creating vm: %s" %
                        task.get_error_message())

    # Here you should power your VM (refer to the pysphere documentation)
    # So it boots from the specified ISO location
    try:
        new_vm = s.get_vm_by_name(opts.name)
        connect_vm_cdroms(new_vm, s)
        try:
            new_vm.power_on()
        except Exception as e:
            print "Failed to power-on the new VM using:", opts.name
            print "Exception:", str(e)
    except Exception as e:
        print "Failed to locate the new VM using:", opts.name
        print "Exception:", str(e)
    # disconnect from the server
    s.disconnect()


def main():
    opts = options()

    # CONNECTION PARAMTERS
    server = opts.esx_host
    user = opts.user
    password = opts.passwd

    # REQUIRED PARAMETERS
    vmname = opts.name
    template = opts.template
    cd_iso_location = opts.iso

    datastorename = opts.datastore  # if None, will use the first datastore available

    # CONNECT TO THE SERVER
    s = VIServer()
    s.connect(server, user, password)

    # Clone the VM.
    try:
        template_vm = s.get_vm_by_name(template)
    except Exception as e:
        print "Failed to locate the template."
        print "Exception:", str(e)
        sys.exit(1)

    vm = template_vm.clone(vmname, power_on=False)
    cdrom = None

    for dev in vm.properties.config.hardware.device:
        if dev._type == "VirtualCdrom":
            cdrom = dev._obj
            break

    change_cdrom_type(cdrom, "ISO", "[%s] %s" % (datastorename, cd_iso_location))
    apply_changes(vm, s, cdrom)

    # Here you should power your VM (refer to the pysphere documentation)
    # So it boots from the specified ISO location
    try:
        new_vm = s.get_vm_by_name(opts.name)
        connect_vm_cdroms(new_vm, s)
        try:
            new_vm.power_on()
        except Exception as e:
            print "Failed to power-on the new VM using:", opts.name
            print "Exception:", str(e)
    except Exception as e:
        print "Failed to locate the new VM using:", opts.name
        print "Exception:", str(e)
    # disconnect from the server
    s.disconnect()

if __name__ == "__main__":
    main()
