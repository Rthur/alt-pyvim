Ansible vSphere Operations with pyVim
=====================================

Ansible is a radically simple configuration-manaagement, deployment, task-execution and multinode orchestration framework. Its module design enables to extend core functionality with custom or specific needs.

This sub-project extends Ansible for play execution against vSphere using pyVim - the Pure Python Vim clone.

Modules
=======
The following modules have been implemented using the underlying pyVim module:

pyvim_facts.py  pyvim_mount_cd.py  pyvim_power.py  pyvim_umount_cd.py
  - fact gathering (pyvim_facts)
  - copy file to datastore (pyvim_copy)
  - mount iso (pyvim_mount_cd)
  - umount iso (pyvim_umount_cd)
  - change virtual machine powerState (pyvim_power)

These modules will not work with python-requests 2.7.0. It has been tested with 2.9.1, 2.12.0

DISCLAIMER
==========
Please note: all tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. We disclaim any and all warranties, either express or implied, including but not limited to any warranty of noninfringement, merchantability, and/ or fitness for a particular purpose. We do not warrant that the technology will meet your requirements, that the operation thereof will be uninterrupted or error-free, or that any errors will be corrected.

Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.

You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.
