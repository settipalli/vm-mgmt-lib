#!/usr/bin/env python

# ==============================================================================
# Name          :   fabfile.py
#
# Description   :   A fabric script to delete the ISO file from the ESXi host.
#                   If you prefer to reuse this library, the values in the file
#                   like the name of the server should be updated.
#
# Version       :   1.0.0
#
# Author        :   Santhoshkumar Settipalli
#
# Change log    :
#   25-Feb-2013 :    Santhoshkumar Settipalli (santhosh.settipalli@gmail.com)
#                    Initial version.
#
# ==============================================================================

from fabric.api import *
from fabric.state import env
from fabric.contrib import files
import settings

env.user = settings.VCENTER_SERVERS['VM-Server-Name-Key'].username
env.password = settings.VCENTER_SERVERS['VM-Server-Name-Key'].password
env.hosts = [settings.VCENTER_SERVERS['VM-Server-Name-Key'].ip, ]
env.shell = "/bin/sh -c"

def delete_iso_file(product=None, filename=None):
    if product == None:
        print "Nothing to delete. Empty product name."
        return

    if filename == None:
        print "Nothing to delete. Empty filename."
        return

    if env.host_string == settings.VCENTER_SERVERS['VM-Server-Name-Key'].ip:
        path = "/vmfs/volumes/datastore1/iso/%s/%s" % (product, filename) 
        
        if not files.exists(path):
            print "Could not find %s. Nothing to delete." % path

        cmd = "rm -f %s" % path
        print "About to execute %s" % cmd
        run(cmd)
        print "Deleted %s successfully." % path
