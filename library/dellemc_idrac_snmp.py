#! /usr/bin/python
# _*_ coding: utf-8 _*_

#
# Copyright (c) 2017 Dell Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: dellemc_idrac_snmp
short_description: Configure SNMP settings on iDRAC
version_added: "2.3"
description:
    - Configures SNMP settings on iDRAC
options:
    idrac_ip:
        required: False
        description: iDRAC IP Address
        default: None
    idrac_user:
        required: False
        description: iDRAC user name
        default: None
    idrac_pwd:
        required: False
        description: iDRAC user password
        default: None
    idrac_port:
        required: False
        description: iDRAC port
        default: None
    share_name:
        required: True
        description: CIFS or NFS Network share
    share_user:
        required: True
        description: Network share user in the format user@domain
    share_pwd:
        required: True
        description: Network share user password
    share_mnt:
        required: True
        description: Local mount path of the network file share with
        read-write permission for ansible user
    snmp_agent_enable:
        required: False
        description: SNMP Agent status
        - if C(enabled), will enable the SNMP Agent
        - if C(disabled), will disable the SNMP Agent
        choices: ['enabled', 'disabled']
        default: 'enabled'
    snmp_protocol:
        required: False
        description: SNMP protocol supported
        - if C(all), will enable support for SNMPv1, v2 and v3 protocols
        - if C(SNMPv3), will enable support for only SNMPv3 protocol
        choices: ['all', 'SNMPv3']
        default: 'all'
    snmp_agent_community:
        required: False
        description: SNMP Agent community string
        default: 'public'
    snmp_discover_port:
        required: False
        description: SNMP discovery port
        default: 161
    snmp_trap_port:
        required: False
        description: SNMP trap port
        default: 162
    snmp_trap_format:
        required: False
        description: SNMP trap format
        - if C(SNMPv1), will configure iDRAC to use SNMPv1 for sending traps
        - if C(SNMPv2), will configure iDRAC to use SNMPv2 for sending traps
        - if C(SNMPv3), will configure iDRAC to use SNMPv3 for sending traps
        choices: ['SNMPv1', 'SNMPv2', 'SNMPv3']
        default: 'SNMPv1'
    state:
        description:
        - if C(present), will perform create/add/enable operations
        - if C(absent), will perform delete/remove/disable operations
        choices: ['present', 'absent']
        default: 'present'

requirements: ['omsdk']
author: "anupam.aloke@dell.com"

"""

EXAMPLES = """
---
- name: Configure SNMP
    dellemc_idrac_snmp:
       idrac_ip:             "192.168.1.1"
       idrac_user:           "root"
       idrac_pwd:            "calvin"
       share_name:           "\\\\10.20.30.40\\share\\"
       share_user:           "user1"
       share_pwd:            "password"
       share_mnt:            "/mnt/share"
       snmp_agent_enable:    "enabled"
       snmp_protocol:        "all"
       snmp_agent_community: "public"
       snmp_discovery_port:  161
       snmp_trap_port:       162
       state:                "present"
"""

RETURNS = """
---
"""

from ansible.module_utils.basic import AnsibleModule

# Setup iDRAC Network File Share
# idrac: iDRAC handle
# module: Ansible module
#
def _setup_idrac_nw_share (idrac, module):

    from omsdk.sdkfile import FileOnShare
    from omsdk.sdkcreds import UserCredentials

    myshare = FileOnShare(module.params['share_name'],
                          module.params['share_mnt'],
                          isFolder=True)

    myshare.addcreds(UserCredentials(module.params['share_user'],
                                     module.params['share_pwd']))

    return idrac.config_mgr.set_liason_share(myshare)

# iDRAC SNMP Configuration
# idrac: iDRAC handle
# module: Ansible module
#
# Supports check_mode
def setup_idrac_snmp (idrac, module):

    msg = {}
    msg['changed'] = False
    msg['failed'] = False
    msg['msg'] = {}
    err = False

    try:
        # Check first whether local mount point for network share is setup
        if idrac.config_mgr.liason_share is None:
             if not  _setup_idrac_nw_share (idrac, module):
                 msg['msg'] = "Failed to setup local mount point for network share"
                 msg['failed'] = True
                 return msg

        # TODO : Check if the SNMP configuration parameters already exists
        exists = False

        if module.params["state"] == "present":
            if module.check_mode or exists:
                msg['changed'] = not exists
            else:
                msg['msg'] = idrac.config_mgr.enable_snmp(
                                        module.params['snmp_agent_community'],
                                        module.params['snmp_discovery_port'],
                                        module.params['snmp_trap_port'],
                                        module.params['snmp_trap_format'])

        else:
            if module.check_mode or not exists:
                msg['changed'] = exists
            else:
                msg['msg'] = idrac.config_mgr.disable_snmp()

        if "Status" in msg['msg']:
            if msg['msg']['Status'] == "Success":
                msg['changed'] = True
            else:
                msg['failed'] = True

    except Exception as e:
        err = True
        msg['msg'] = "Error: %s" % str(e)
        msg['failed'] = True

    return msg, err

# Main
def main():
    from ansible.module_utils.dellemc_idrac import iDRACConnection

    module = AnsibleModule (
            argument_spec = dict (

                # iDRAC Handle
                idrac = dict (required = False, type = 'dict'),

                # iDRAC Credentials
                idrac_ip   = dict (required = False, default = None, type = 'str'),
                idrac_user = dict (required = False, default = None, type = 'str'),
                idrac_pwd  = dict (required = False, default = None,
                                   type = 'str', no_log = True),
                idrac_port = dict (required = False, default = None),

                # Network File Share
                share_name = dict (required = True, default = None),
                share_user = dict (required = True, default = None),
                share_pwd  = dict (required = True, default = None),
                share_mnt  = dict (required = True, default = None),

                # SNMP Configuration
                snmp_agent_enable = dict (required = False,
                                    choice = ['enabled', 'disabled'],
                                    default = 'enabled',
                                    type = 'str'),
                snmp_protocol = dict (required = False,
                                    choice = ['all', 'SNMPv3'],
                                    default = 'all',
                                    type = 'str'),
                snmp_agent_community = dict (required = False,
                                            default = 'public', type = 'str'),
                snmp_discovery_port = dict (required = False,
                                            default = 161, type = 'int'),
                snmp_trap_port = dict (required = False, default = 162,
                                        type = 'int'),
                snmp_trap_format = dict (required = False,
                                        choice = ['SNMPv1','SNMPv2','SNMPv3'],
                                        default = 'SNMPv1',
                                        type = 'str'),

                state = dict (required = False, choice = ['present','absent'])
            ),
            supports_check_mode = True)

    # Connect to iDRAC
    idrac_conn = iDRACConnection (module)
    idrac = idrac_conn.connect()

    # Configure SNMP
    msg, err = setup_idrac_snmp (idrac, module)

    # Disconnect from iDRAC
    idrac_conn.disconnect()

    if err:
        module.fail_json(**msg)
    module.exit_json(**msg)

if __name__ == '__main__':
    main()
