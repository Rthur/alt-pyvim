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

