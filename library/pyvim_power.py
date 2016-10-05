#!/usr/bin/python

DOCUMENTATION = '''
---
author: Arthur Reyes
module: pyvim_power
description:
  - Change power state of Virtual Machine while optionally setting boot to cd.
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
  state:
    description:
      - New powerState of Virtual Machine. Suspend actions not implemented.
    choices: [ 'reset', 'poweredOff', 'poweredOn' ]
    required: true
  bootcdrom:
    description:
      - Determines whether the system will be booted from cdrom. Due to
        limitations in the summary returned from vm query bootorder is not
        properly populated in output. Not setting this will cause the module 
        to clear any custom boot order. In other words, the Virtual Machine
         will revert to BIOS settings for startup order.
    required: false
    choices: [ True, Flase ]
    default: False
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
      uuid = dict(required=True),
      state = dict(required=True),
      bootcdrom = dict(required=False, default=False),
    )
  )

  host = module.params.get('host')
  port = module.params.get('port')
  login = module.params.get('login')
  password = module.params.get('password')
  uuid = module.params.get('uuid')
  state = module.params.get('state')
  bootcdrom = module.params.get('bootcdrom')

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

  if bootcdrom == True:
    bootorder = 'cd'
  else:
    bootorder = ''

  # set the boot order
  bo = vim.option.OptionValue(key='bios.bootDeviceClasses', 
                              value=bootorder)
  spec = vim.vm.ConfigSpec()
  spec.extraConfig = [bo]
  task = target.ReconfigVM_Task(spec=spec)
  tasks.wait_for_tasks(si, [task])

  if task.info.state != 'success':
    module.fail_json(msg='setting bootorder to "%s" failed' % (bootorder))
 
  current_state = target.summary.runtime.powerState

  if current_state == 'suspended':
    module.fail_json(msg='Changing powerState to %s from suspended state not implemented' % (state)) 

  if state != 'reset' and state == current_state:
    module.exit_json(changed=False)

  if state == 'reset' and current_state == 'poweredOn':
    task = target.ResetVM_Task()
  elif state in [ 'reset', 'poweredOn' ] and current_state == 'poweredOff':
    task = target.PowerOnVM_Task()
  elif state == 'poweredOff':
    task = target.PowerOffVM_Task()
  else:
    module.fail_json(msg='unrecognized powerState requested: %s' % (state))
    
  tasks.wait_for_tasks(si, [task])

  if task.info.state != 'success':
    module.fail_json(msg='change Virtual Machine powerState to %s failed' % (state))
  else:
    module.exit_json(changed=True)

#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()

