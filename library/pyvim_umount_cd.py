#!/usr/bin/python

DOCUMENTATION = '''
---
author: Arthur Reyes
module: pyvim_umount_cd
description: 
  - unmount an iso on Virtual Machine
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
  uuid:
    description:
      - the instanceUuid of the guest. Useful to identify a unique guest
        when multiple virtual machines with the same name exist across
        clusters.
    required: true
  device:
    description:
      - the virtual device name where media will be mounded.
    required: true
'''

import atexit
import sys
import requests

try:
  from pyVim import connect
  from pyVmomi import vmodl
  from pyVmomi import vim
  from tools import cli
  from tools import tasks

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
      uuid = dict(required=False, default=None),
      device = dict(required=True),
    )
  )

  host = module.params.get('host')
  port = module.params.get('port')
  login = module.params.get('login')
  password = module.params.get('password')
  uuid = module.params.get('uuid')
  device = module.params.get('device')

  context = connect.ssl.SSLContext(connect.ssl.PROTOCOL_TLSv1)
  context.verify_mode = connect.ssl.CERT_NONE
  requests.packages.urllib3.disable_warnings()

  try:
    si = connect.SmartConnect(host=host, port=int(port), user=login, 
                              pwd=password, sslContext=context)
  except Exception, e:
    module.fail_json(msg='Failed to connect to %s: %s' % (host, e))

  atexit.register(connect.Disconnect, si)
  content = si.RetrieveContent()
  container = content.viewManager.CreateContainerView(content.rootFolder, 
              [vim.VirtualMachine], True)
  
  target = None
  children = container.view
  for child in children:
    if uuid and child.summary.config.instanceUuid == uuid:
        target = child

  if not target:
      module.fail_json(msg='guest machine not found: %s' % (uuid))

  for dev in target.config.hardware.device:
    if isinstance(dev, vim.vm.device.VirtualCdrom) \
        and dev.deviceInfo.label == device:
      cdrom = dev

  if not cdrom:
      module.fail_json(msg='virtual device not found: %s' % (device))

  if hasattr(cdrom.backing, 'RemotePassthroughBackingInfo'):
    module.exit_json(changed=False)

  cdrom_spec = vim.vm.device.VirtualDeviceSpec()
  cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
  cdrom_spec.device = vim.vm.device.VirtualCdrom()
  cdrom_spec.device.controllerKey = cdrom.controllerKey
  cdrom_spec.device.key = cdrom.key
  cdrom_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
  cdrom_spec.device.backing = \
    vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
  cdrom_spec.device.connectable.allowGuestControl = True

  container.Destroy()

  dev_changes = []
  dev_changes.append(cdrom_spec)
  spec = vim.vm.ConfigSpec()
  spec.deviceChange = dev_changes
  task = target.ReconfigVM_Task(spec=spec)
  tasks.wait_for_tasks(si, [task])

  if str(dev_changes[0]).find('vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo') > 0:
    module.exit_json(changed=True)
  else:
    module.fail_json(msg='Device in unknown state: %s, %s' % (device, dev_changes[0]))

#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()

