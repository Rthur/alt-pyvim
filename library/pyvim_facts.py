#!/app/ansible2/bin/python
# -* coding: utf-8 -*-

DOCUMENTATION = '''
---
author: Arthur Reyes
module: pyvim_facts
description:
  - This module gathers and correlates a larger number of useful facts 
    from a specified guest on VMWare vSphere.
version_added: "0.1"
requirements:
  - pyVim
notes:
  - This module disables SSL Security and warnings for invalid certificates.
  - Tested with Ansible 2.0.1.0
options:
  host:
    description:
      - The vSphere server that manages the cluster where the guest is 
        located on.
    required: true
    aliases: ['vsphere']
  login:
    description:
      - A login name which can authenticate to the vSphere cluster.
    required: true
    aliases: ['admin']
  password:
    description:
      - The password used to authenticate to the vSphere cluster.
    required: true
    aliases: ['secret']
  port:
    description:
      - The port the vSphere listens on.
    required: false
    default: 443
  guest:
    description:
      - The name of the guest to gather facts from the vSphere cluster.
        Apparently the same guest name can exist in multiple datacenters, so
        this value is ignored if uuid is defined.
    required: true
  uuid:
    description:
      - the instanceUuid of the guest. Useful to identify a unique guest 
        when multiple virtual machines with the same name exist across 
        clusters. If not defined and multiple guests are returned by a query
        then this module will fail. If defined, guest name is ignored.
    required: false
    default: null
'''

import atexit
import sys
import requests

try:
    from pyVim import connect
    from pyVmomi import vmodl
    from pyVmomi import vim

except ImportError:
    print "failed=True msg='pyvmoni python module unavailable'"
    sys.exit(1)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True, aliases=['vsphere']),
            port = dict(required=False, default=443),
            login = dict(required=True, aliases=['admin']),
            password = dict(required=True, aliases=['secret']),
            guest = dict(required=True),
            uuid = dict(required=False, default=None),
        )
    )

    host = module.params.get('host')
    port = module.params.get('port')
    login = module.params.get('login')
    password = module.params.get('password')
    guest = module.params.get('guest')
    uuid = module.params.get('uuid')

    context = connect.ssl.SSLContext(connect.ssl.PROTOCOL_TLSv1)
    context.verify_mode = connect.ssl.CERT_NONE
    requests.packages.urllib3.disable_warnings()

    try:
        service_instance = connect.SmartConnect(host=host,
                                                port=int(port),  
                                                user=login,
                                                pwd=password,
                                                sslContext=context)
    except Exception, e:
        module.fail_json(msg='Failed to connect to %s: %s' % (host, e))

    atexit.register(connect.Disconnect, service_instance)

    content = service_instance.RetrieveContent()
    VMView = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)

    vms = []
    children = VMView.view
    VMView.Destroy()
    for child in children:
        if uuid and child.summary.config.instanceUuid == uuid:
            # defining a uuid in the module params overrides guest name
            vms.append(child)
            break
        elif not uuid and child.summary.config.name == guest:
            vms.append(child)

    if len(vms) == 1:
        vm = vms[0]
        sane_disk = vm.summary.config.vmPathName.replace('[', '').replace('] ', '/')
        sane_path = "/".join(sane_disk.split('/')[0:-1])

        #sanitize the datastore name so we can use it as search criteria
        datastore = sane_path.split('/')[0]

        # corrolate datacenter facts
        DCView = content.viewManager.CreateContainerView( content.rootFolder, [vim.Datacenter],
                                                          True )
        for dc in DCView.view:
          DSView = content.viewManager.CreateContainerView( dc, [vim.Datastore], True )
          for ds in DSView.view:
            if ds.info.name == datastore:
              vm_host_datacenter = dc.name
              break

        DCView.Destroy()
        DSView.Destroy()

        # corrolate datastore facts
        HSView =  content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
        esxhosts = HSView.view
        HSView.Destroy()
        for esxhost in esxhosts:
          if esxhost.name == vm.summary.runtime.host.summary.config.name:
            vm_host = esxhost
            host_storage = vm_host.configManager.storageSystem
            host_storage_info = host_storage.fileSystemVolumeInfo.mountInfo
            for mount in host_storage_info:
              if str(mount.volume.name) == str(datastore):
                vm_host_datastore = mount.volume.name
                vm_host_datastore_capacity = mount.volume.capacity
                vm_host_datastore_max_blocks = mount.volume.maxBlocks
                break
            break

        facts = {
            'general' : { 
              'name': vm.summary.config.name,
              'full_name': vm.summary.config.guestFullName,
              'id': vm.summary.config.guestId,
              'instance_uuid': vm.summary.config.instanceUuid,
              'bios_uuid': vm.summary.config.uuid,
              'processor_count': vm.summary.config.numCpu,
              'memtotal_mb': vm.summary.config.memorySizeMB,
              'datacenter': vm_host_datacenter,
            }
        }

        facts['vm_state'] = {
            'host': vm.summary.runtime.host.summary.config.name,
            'power': vm.summary.runtime.powerState,
            'status': vm.summary.overallStatus,
        }

        facts['hm_datastore'] = {
            'name': vm_host_datastore,
            'capacity': vm_host_datastore_capacity,
            'max_block_size': vm_host_datastore_max_blocks,
            'guest_disk':  vm.summary.config.vmPathName,
            'guest_path_sane': sane_path,
            'guest_path': "/".join((vm.summary.config.vmPathName).split('/')[0:-1]),
            'guest_disk_sane': sane_disk,
        }

        facts['vm_bios'] = {
            'bootOrder': vm.config.bootOptions.bootOrder,
        }
            
        # enumerate network
        ints = {}
        intidx = 0
        for entry in vm.config.hardware.device:
          if not hasattr(entry, 'macAddress'): 
            continue

          int_name = 'eth' + str(intidx)
          ints[int_name] = {
            'address_type' : entry.addressType,
            'mac' : entry.macAddress,
            'mac_upper' : entry.macAddress.upper(),
            'mac_dash': entry.macAddress.replace(':', '-'),
            'summary': entry.deviceInfo.summary,
          }

          intidx += 1

        facts['vm_network'] = ints

        # enumerate virtual medial
        virtual_devices = {}
        virtual_media_types = ['CD/DVD drive', 'USB controller', 'Floppy drive' ]
        for entry in vm.config.hardware.device:
          if hasattr(entry, 'macAddress'):
            continue

          if not any(device in entry.deviceInfo.label for device in virtual_media_types):
            continue

          virtual_devices[entry.deviceInfo.label] = {
            'summary': entry.deviceInfo.summary,
            'unitNumber': entry.unitNumber,
          }

        facts['vm_removeable_media'] = virtual_devices

    elif len(vms) == 0:
        module.fail_json(msg='no virtual machines found')
    else:
        # we only want a single unique host.
        module.fail_json(msg='guest lookup returned multiple virtual machines: %s'(vms))

    module.exit_json(ansible_facts=facts)

#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
