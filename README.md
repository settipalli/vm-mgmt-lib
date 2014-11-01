vm-mgmt-lib
===========

A library that can be used to create, delete and manipulate virtual machines using pysphere.


Description:
-----------
This is a collection of python scripts that can be utilized to manage the deployment and deletion of a virtual machine in VMware environment.

The scripts extensively utilize the [`python-pyshere`](https://pypi.python.org/pypi/pysphere) library created by Sebastian Tello. I have extensively utilized some of the sample code posted by Sebastian Tello in the pysphere google-groups in response to queries by others.


Description of files:
--------------------
Please note that these scripts are adjusted to work in my environment which may or may not be same as yours. They may have to be updated to suit your requirements.

`settings.py`
    Common settings to be used by VM management library.

`vm-mgmt-create.py`
    Can be used to create and manipulate VMs.

`vm-mgmt-delete.py`
    Can be used to delete VMs.

`fabfile.py`
    A fabric script to delete the ISO file from the ESXi host. If you prefer to reuse this library, the values in the file like the name of the server, path of the datatore in the ESXi server etc., should be updated.

`detect_installation_completion.py`
    Can be used to detect the completion of OS installation in VMs and perform additional steps such as ejecting the CD-ROM drive from within the OS and then disconnecting the Virtual CD-ROM drive from the VM configuration.

Reference:
---------
1. [https://code.google.com/p/pysphere/](https://code.google.com/p/pysphere/)
