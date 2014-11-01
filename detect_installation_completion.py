#!/usr/bin/env python

# ==============================================================================
# Name          :   detect_installation_completion.py
#
# Description   :   Common library to detect completion of OS installation in
#                   VMs and perform additional steps such as ejecting the
#                   CD-ROM drive from within the OS and then disconnecting the
#                   Virtual CD-ROM drive from the VM configuration.
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
import time
import settings
from optparse import OptionParser
from pysphere import VIServer, VIProperty
from pysphere.resources import VimService_services as VI
from pysphere.vi_task import VITask
import logging
import logging.handlers

# Reference to logging modules.
logger = None
handler = None

logging_levels = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def setup_logger():
    global logger, handler
    # Setup logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger('vm_mgmt_lib')
    logger.setLevel(logging_levels.get(settings.LOG_LEVEL))

    # Add the log message handler to the logger (1 MB per file and upto 10
    # files)
    handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=1048576, backupCount=10)
    handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)


def log(level='debug', msg=""):
    global logger
    logger.log(logging_levels.get(level), msg)


def options():
    parser = OptionParser()
    parser.add_option("--login", dest="login", choices=settings.GUEST_LOGIN_INFO.keys(
    ), help="Product type of the VM. This has some defaults (login username and password) which can be overridden with the other options. Supported choices: " + str(settings.GUEST_LOGIN_INFO.keys()))
    parser.add_option(
        "--vcenter", dest="vcenter", type="choice", choices=settings.VCENTER_SERVERS.keys(), help="Choose a vCenter configuration. Supported choices: " + str(settings.VCENTER_SERVERS.keys()))
    parser.add_option("--name", dest="name", help="Name of the VM.")
    parser.add_option("--guest_login_username", dest="username",
                      help="Username to be used to login to the Guest.")
    parser.add_option(
        "--guest_login_password", dest="password", help="Password for the username that is used to login to the Guest.")
    parser.add_option("--get_ip", action="store_true", dest="fetch_ip")
    opts, args = parser.parse_args()

    if not opts.login:
        log(level="error",
            msg="Cannot continue without Guest Login Information. Use --login.")
        sys.exit(1)

    if not opts.vcenter:
        log(level="error",
            msg="Cannot continue without vCenter or ESXi host Information. Use --vcenter.")
        sys.exit(1)

    if not opts.name:
        log(level="error",
            msg="Cannot continue without Guest VM Name. Use --name.")
        sys.exit(1)

    if not opts.fetch_ip:
        opts.fetch_ip = False

    vcenter_present = opts.vcenter and opts.vcenter in settings.VCENTER_SERVERS
    if vcenter_present:
        vcenter = settings.VCENTER_SERVERS[opts.vcenter]
        opts.esx_host = vcenter.ip
        opts.user = vcenter.username
        opts.passwd = vcenter.password
    else:
        print
        log(level="error",
            msg="ERROR: no support for a deployment where a vCenter or ESXi host server is not available.")
        print
        sys.exit(1)

    login_present = opts.login and opts.login in settings.GUEST_LOGIN_INFO
    if login_present:
        logintype = settings.GUEST_LOGIN_INFO[opts.login]
        opts.username = opts.username or logintype.username
        opts.password = opts.password or logintype.password

    # log(level="info", msg="Identified options:", opts)
    return opts


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
        client = VI.ns0.VirtualCdromRemoteAtapiBackingInfo_Def(
            "client").pyclass()
        client.set_element_deviceName("")
        dev.set_element_backing(client)


def disconnect_vm_cdroms(vm, server):
    connected_cdroms = []

    for dev in vm.properties.config.hardware.device:
        if dev._type == "VirtualCdrom":
        # and dev.connectable.connected:
        # if dev._type == "VirtualCdrom" and dev.connectable.startConnected:
            d = dev._obj
            try:
                d.Connectable.set_element_connected(False)
                d.Connectable.set_element_startConnected(False)
                connected_cdroms.append(d)
            except:
                log(level="warning", msg="%s: no virtual cd roms found." %
                    vm.properties.name)

    if not connected_cdroms:
        log(level="info", msg="%s: has no connected cd roms" %
            vm.properties.name)
        return

    request = VI.ReconfigVM_TaskRequestMsg()
    _this = request.new__this(vm._mor)
    _this.set_attribute_type(vm._mor.get_attribute_type())
    request.set_element__this(_this)
    spec = request.new_spec()
    dev_changes = []

    for dev in connected_cdroms:
        change_cdrom_type(dev, "CLIENT DEVICE")
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
        log(level="info", msg="%s: successfully reconfigured" %
            vm.properties.name)
    elif status == task.STATE_ERROR:
        log(level="error", msg="%s: Error reconfiguring vm" %
            vm.properties.name)


def check_count(count, wait_for):
    if count >= wait_for:
        log(level="warning", msg="Exceeded %s timeout." % str(wait_for))
        log(level="error", msg="Aborted.")


def main():

    setup_logger()

    log(level="info",
        msg="===================================================")
    log(level="info", msg="detect_installation_completion logger initialized.")

    opts = options()

    # CONNECTION PARAMTERS
    server = opts.esx_host
    user = opts.user
    password = opts.passwd

    # REQUIRED PARAMETERS
    vmname = opts.name

    # CONNECT TO THE SERVER
    s = VIServer()
    s.connect(server, user, password)

    log(level="info", msg="Attempting to locate the guest VM: %s" % vmname)
    count = 1
    wait_for = 10
    while count < wait_for:
        count += 1
        try:
            guest_vm = s.get_vm_by_name(opts.name)
            if guest_vm:
                break
        except Exception as e:
            if count >= wait_for:
                log(level="error", msg="Failed to locate the new VM (%s) even after %s seconds." %
                    (vmname, str(wait_for)))
                log(level="info", msg="Please login to the EXSi server and fix the issue. Exception: %s" %
                    str(e))
                sys.exit(1)

        time.sleep(1)
        log(level="info", msg="Elapsed %s seconds ..." % str(count))

    check_count(count, wait_for)
    log(level="info", msg="Located VM: %s" % vmname)
    log(level="info", msg="Waiting for the OS installation to complete...")
    log(level="info", msg="Will wait for about 60 minutes (at max) ...")

    wait_for = 3600  # 1 hour.
    log(level="info",
        msg="Note: There will be no output as the process would be blocked in waiting state until the Guest OS responds.")
    log(level="info",
        msg="Will automatically timeout after an hour (at max) ...")
    try:
        guest_vm.wait_for_tools(timeout=wait_for)
    except Exception as e:
        if count >= wait_for:
            log(level="error", msg="Failed to get OS installation status in the new VM (%s) even after %s seconds." %
                (vmname, str(wait_for)))
            log(level="info", msg="Please login to the EXSi server and fix the issue. Exception: %s" %
                str(e))
            sys.exit(1)

    log(level="info", msg="Received response from the Guest OS.")
    log(level="info",
        msg="Attempting to login in the Guest to check the status of the OS instalaltion (timeout 5 minutes) ...")
    count = 1
    wait_for = 300  # 5 minutes
    while count < wait_for:
        try:
            guest_vm.login_in_guest(opts.username, opts.password)
            break
        except Exception as e:
            if count >= wait_for:
                log(level="error", msg="Failed to login to the Guest (%s) even after %s seconds." %
                    (vmname, str(wait_for)))
                log(level="info", msg="Please login to the EXSi server and fix the issue. Exception: %s" %
                    str(e))
                sys.exit(1)
        count += 1
        time.sleep(1)
        log(level="info", msg="Elapsed %s seconds ..." % str(count))

    check_count(count, wait_for)
    log(level="info", msg="Successfully logged into guest.")
    log(level="info",
        msg="Checking the progress of the OS installation (will timeout after 30 minutes (at max)) ...")
    log(level="info", msg="OS installation is still in progress.")
    log(level="info",
        msg="Waiting for it to complete (will timeout after 60 minutes (at max)) ...")
    count = 1
    wait_for = 3600  # 60 minutes
    filename = "/etc/INSTALLATION_COMPLETED"

    while count < wait_for:
        try:
            flag_file = guest_vm.list_files(filename)
            if flag_file[0]['path'] == filename:
                log(level="info",
                    msg="OS installation has completed. Successfully.")
                break
        except Exception as e:
            if count >= wait_for:
                log(level="error", msg="OS installation is still in progress in %s even after %s seconds. This is not expected." %
                    (vmname, str(wait_for)))
                log(level="info", msg="Please login to the EXSi server and fix the issue. Exception: %s" %
                    str(e))
                sys.exit(1)

        count += 180
        time.sleep(180)
        log(level="info", msg="Elapsed %s seconds ..." % str(count))

    check_count(count, wait_for)

    if opts.fetch_ip is True:

        vm_ip = guest_vm.get_property(
            'net', from_cache=False)[0]['ip_addresses'][0]
        log(level="info", msg="IP address of the deployed VM: %s" % str(vm_ip))

        ip_file_path = settings.DEPLOYED_VM_IP_SAVE_FOLDER + "/%s.txt" % vmname
        try:
            with open(ip_file_path, 'w') as f:
                f.write(vm_ip)
                log(level="info", msg="Saved the IP of the deployed machine in: %s" %
                    ip_file_path)
                f.close()
        except:
            log(level="error", msg="Failed to save the IP information in %s. Please try again." %
                ip_file_path)

    else:  # if opts.fetch_ip == False

        try:
            network_fix = guest_vm.list_files('/etc/init.d/vm_network_fix')
            log(level="info", msg="Network fix already exists. Nothing needs to be done.")
        except:
            try:
                # Network fix does not exist.
                log(level="info", msg="Network fix does not exist. Uploading vm_network_fix.")
                guest_vm.send_file('vm_network_fix', '/etc/init.d/vm_network_fix', overwrite=True)
                log(level="info", msg="Upload of vm_network_fix successful. Changing permissions.")
                guest_vm.start_process('/bin/chmod', args=[
                                   '755', 'vm_network_fix'], cwd='/etc/init.d')
                time.sleep(1)
                log(level="info", msg="Changing permissions successful. Adding the daemon to start-up sequence.")
                guest_vm.start_process('/sbin/chkconfig', args=[
                                   '--add', 'vm_network_fix'], cwd='/etc/init.d')
                time.sleep(1)
                log(level="info", msg="Updating start-up sequence successful. Starting the daemon.")
                guest_vm.start_process('/sbin/service', args=[
                                   'vm_network_fix', 'start'], cwd='/etc/init.d')
                time.sleep(1)
                log(level="info", msg="Daemon process started successfully.")
            except Exception as e:
                log(level="error", msg="Failed to upload vm_network_fix and start the daemon. Exception: " + str(e))

        log(level="info",
            msg="Waiting for 60 seconds so that all services start successfully.")
        count = 1
        wait_for = 60
        while count < wait_for:
            count += 2
            time.sleep(2)
            log(level="info", msg="Elapsed %s seconds ..." % str(count))

        log(level="info", msg="All services should be up and running now ...")
        log(level="info",
            msg="Issuing a graceful shutdown request to the Guest.")
        try:
            guest_vm.start_process('/sbin/shutdown', args=[
                                   '-h', 'now'], cwd='/root')
            time.sleep(1)
            count = 1
            wait_for = 900  # 30 minutes.
            log(level="info", msg="Waiting for the Guest to power-off ...")
            while guest_vm.is_powered_off() is False:
                time.sleep(1)
                count += 1
                log(level="info", msg="Elapsed %s seconds ..." % str(count))
                if count >= wait_for:
                    log(level="warning",
                        msg="Its been 30 minutes and yet the system did not poweroff. This not expected.")
                    log(level="warning",
                        msg="OVFTool may hard-poweroff the VM while attempting to create an OVA of it.")
                    break
            if count < wait_for:
                log(level="info", msg="%s powered off successfully." % vmname)
        except Exception as e:
            log(level="error",
                msg="Could not issue a graceful shutdown request to the guest.")
            log(level="warning",
                msg="OVFTool may hard-poweroff the VM while attempting to create an OVA of it.")
            log(level="error", msg="Exception: %s" % str(e))

        # Disconnect CDROM device from the VM.
        try:
            disconnect_vm_cdroms(guest_vm, s)
            log(level="info", msg="Disconnected Virtual CDROM from %s successfully." %
                vmname)
        except:
            log(level="error", msg="Exception while attempting to disconnect the virtual CD rom of %s." %
                vmname)
            log(level="error", msg="Exception: %s" % str(e))

    # disconnect from the server
    s.disconnect()

    sys.exit(0)

if __name__ == "__main__":
    main()
