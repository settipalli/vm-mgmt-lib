#!/usr/bin/env python

# ==============================================================================
# Name          :   vm-mgmt-delete.py
#
# Description   :   Common library to delete VMs.
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
    parser.add_option("--name", dest="name", help="Name for this VM.")
    parser.add_option(
        "--vcenter", dest="vcenter", type="choice", choices=settings.VCENTER_SERVERS.keys(), help="Choose a vCenter configuration. Supported choices: " + str(settings.VCENTER_SERVERS.keys()))
    parser.add_option("--user", dest="user", help="Username to connect to ESX Server.")
    parser.add_option("--pass", dest="passwd", help="Password to connect to ESX Server.")
    parser.add_option("--esx-host", dest="esx_host", help="Hostname of ESX Server to connect to.")

    opts, args = parser.parse_args()

    vcenter_present = opts.vcenter and opts.vcenter in settings.VCENTER_SERVERS
    if vcenter_present:
        vcenter = settings.VCENTER_SERVERS[opts.vcenter]
        opts.esx_host = vcenter.ip
        opts.user = vcenter.username
        opts.passwd = vcenter.password
    else:
        print
        print "ERROR: no support for a deployment where a vCenter or ESXi host server is not available."
        print
        sys.exit(1)

    if not opts.name:
        print "Cannot continue without VM Name that is supposed to be deleted. Use --name <Name-of-the-VM>."
        sys.exit(1)

    # print "Identified options:", opts
    return opts


def check_count(count, wait_for):
    if count >= wait_for:
        print "Exceeded %s timeout." % str(wait_for)
        print "Aborted."


def main():
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

    try:
        vm = s.get_vm_by_name(opts.name)
        vm.shutdown_guest()
        
        count = 1
        wait_for = 60
        try: 
            while count < wait_for and vm.is_powered_off() == False:
                count += 1
                time.sleep(1)
                print "Elapsed %s seconds ..." % str(count)

        except Exception as e:
            if count >= wait_for:
                print "Failed to shutdown the VM (%s) even after %s seconds." % (vmname, str(wait_for))
                print "Please login to the EXSi server and fix the issue. Exception: %s" % str(e)
                sys.exit(1)

        check_count(count, wait_for)
    except Exception as e:
        print "Failed to locate and shutdown the new VM using:", opts.name
        print "VM could not be deleted."
        print "Exception:", str(e)

    # Invoke Destroy_Task
    request = VI.Destroy_TaskRequestMsg()
    _this = request.new__this(vm._mor)
    _this.set_attribute_type(vm._mor.get_attribute_type())
    request.set_element__this(_this)
    ret = s._proxy.Destroy_Task(request)._returnval

    # Wait for the task to finish
    task = VITask(ret, s)

    status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
    if status == task.STATE_SUCCESS:
        print "VM successfully deleted from disk"
    elif status == task.STATE_ERROR:
        print "Error removing vm:", task.get_error_message()

    # disconnect from the server
    s.disconnect()

if __name__ == "__main__":
    main()
