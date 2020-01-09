#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, quidame <quidame@poivron.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: iptables_state
short_description: Save iptables state into a file or restore it from a file
version_added: "2.9"
author:
  - quidame <quidame@poivron.org>
description:
  - C(iptables) is used to set up, maintain, and inspect the tables of IP
    packet filter rules in the Linux kernel.
  - This module handles the saving and/or loading of rules. This is the
    same as the behaviour of the C(iptables-save) and C(iptables-restore)
    (or C(ip6tables-save) and C(ip6tables-restore) for IPv6) commands which
    this module uses internally.
options:
  table:
    description:
      - Restore only the named table even if the input stream contains other
        ones.
      - Restrict output to only one table. If not specified, output includes
        all available tables.
    type: str
    choices: [ filter, nat, mangle, raw, security ]
  state:
    description:
      - Whether the firewall state should be saved or restored.
    type: str
    choices: [ saved, restored ]
  counters:
    description:
      - Save or restore the values of all packet and byte counters.
      - When I(True), the module is not idempotent.
    type: bool
    default: false
  noflush:
    description:
      - For I(state=restored), ignored otherwise. Don't flush the previous
        contents of the table. If not specified, restoring iptables rules
        from a file flushes (deletes) all previous contents of the respective
        table.
    type: bool
    default: false
  ip_version:
    description:
      - Which version of the IP protocol this module should apply to.
    type: str
    choices: [ ipv4, ipv6 ]
    default: ipv4
  modprobe:
    description:
      - Specify the path to the modprobe program. By default,
        /proc/sys/kernel/modprobe is inspected to determine the executable's
        path.
    type: path
  path:
    description:
      - The file the iptables state should be saved to.
      - The file the iptables state should be restored from.
      - Required when I(state=saved) or I(state=restored).
    type: path
'''

EXAMPLES = r'''
- name: Get current state of the firewall
  iptables_state:
  register: iptables_state

- name: Display current state of the firewall
  debug:
    var: iptables_state.initial_state

- name: Save current state of the firewall in system file
  iptables_state:
    state: saved
    path: /etc/sysconfig/iptables

- name: Restore firewall state from a file
  iptables_state:
    state: restored
    path: /run/iptables.apply
  async: "{{ ansible_timeout }}"
  poll: 0
'''

RETURN = r'''
applied:
    description: whether or not the wanted state has been successfully applied
    type: bool
    returned: always
initial_state:
    description: the current state of the firewall when module starts
    type: list
    returned: always
restored_state:
    description: the new state of the firewall, when state=restored
    type: list
    returned: always
rollback_complete:
    description: whether or not firewall state is the same than the initial one
    type: bool
    returned: failure
'''


import re
import os
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes


IPTABLES = dict(
        ipv4='iptables',
        ipv6='ip6tables',
)

SAVE = dict(
        ipv4='iptables-save',
        ipv6='ip6tables-save',
)

RESTORE = dict(
        ipv4='iptables-restore',
        ipv6='ip6tables-restore',
)

TABLES = dict(
        filter = ['INPUT', 'FORWARD', 'OUTPUT'],
        mangle = ['PREROUTING','INPUT','FORWARD','OUTPUT','POSTROUTING'],
        nat = ['PREROUTING','INPUT','OUTPUT','POSTROUTING'],
        raw = ['PREROUTING','OUTPUT'],
        security = ['INPUT', 'FORWARD', 'OUTPUT'],
)


# If related kernel modules are not loaded, iptables-save output is empty, so
# it's not reliable to use it *as is* as input for iptables-restore in case of
# rollback. On the other hand, loading these kernel modules is not enough for
# iptables-nft (alternative to iptables-legacy on modern systems at the time
# of writing) to get a usable output for this same purpose.
def initialize_from_null_state(bin_iptables, table=None):
    if not table: table = 'filter'

    PARTCOMMAND = [bin_iptables, '-t', table, '-P']

    for chain in TABLES[table]:
        RESETPOLICY = list(PARTCOMMAND)
        RESETPOLICY.append(chain)
        RESETPOLICY.append('ACCEPT')
        ( rc, out, err ) = module.run_command(RESETPOLICY, check_rc=True)
    return True


# Remove timestamps to ensure idempotency between runs. The removal of other
# dynamic info such as counters is optional. It means that when 'counters' is
# set to True, the module is not idempotent.
def reformat(string, boolean):
    string = re.sub('((^|\n)# (Generated|Completed)[^\n]*) on [^\n]*', '\\1', string)
    if not boolean: string = re.sub('\[[0-9]+:[0-9]+\]', '[0:0]', string)
    string_lines = string.split('\n')
    while '' in string_lines: string_lines.remove('')
    return string_lines


# Write given contents to the given file, and return the old and new checksums
# of the file. The module currently doesn't manage parent directories (so, fail
# if missing) nor the file properties (it does, but poorly with just os.umask).
def writein(filepath, contents):
    b_filepath = to_bytes(filepath, errors='surrogate_or_strict')
    old = None

    if os.path.exists(b_filepath):
        if not os.path.isfile(b_filepath):
            module.fail_json(msg="Destination %s exists and is not a regular file" % (filepath))
        if not os.access(b_filepath, os.W_OK):
            module.fail_json(msg="Desitination %s not writeable" % (filepath))
        old = module.sha1(filepath)
    else:
        dirname = os.path.dirname(b_filepath)
        if not os.path.exists(dirname):
            module.fail_json(msg="Destination parent %s not found" % (dirname))
        if not os.path.isdir(dirname):
            module.fail_json(msg="Destination parent %s not a directory" % (dirname))
        if not os.access(dirname, os.W_OK):
            module.fail_json(msg="Desitination parent %s not writeable" % (dirname))

    try:
        dest = open(filepath, 'w+')
        if type(contents) in [str, int, float]:
            dest.write("%s\n" % (contents))

        elif type(contents) in [list, dict, tuple]:
            for line in contents:
                dest.write("%s\n" % (line))
        dest.close()
    except:
        module.fail_json(msg="Unable to write into %s" % (filepath))

    new = module.sha1(filepath)
    return (old, new)


def main():
    global module
    module = AnsibleModule(
        supports_check_mode=False,
        argument_spec=dict(
            path=dict(type='path'),
            state=dict(type='str', choices=['saved', 'restored']),
            table=dict(type='str', choices=['filter', 'nat', 'mangle', 'raw', 'security']),
            noflush=dict(type='bool', default=False),
            counters=dict(type='bool', default=False),
            modprobe=dict(type='path'),
            ip_version=dict(type='str', choices=['ipv4', 'ipv6'], default='ipv4'),
            _timeout=dict(type='int'),
            _back=dict(type='path'),
        ),
        required_together=[
            ['state', 'path'],
            ['_timeout', '_back'],
        ],
    )

    path = module.params['path']
    state = module.params['state']
    table = module.params['table']
    noflush = module.params['noflush']
    counters = module.params['counters']
    modprobe = module.params['modprobe']
    ip_version = module.params['ip_version']
    _timeout = module.params['_timeout']
    _back = module.params['_back']


    bin_iptables = module.get_bin_path(IPTABLES[ip_version], True)
    bin_iptables_save = module.get_bin_path(SAVE[ip_version], True)
    bin_iptables_restore = module.get_bin_path(RESTORE[ip_version], True)

    os.umask(0o077)
    changed = False
    COMMANDARGS = []

    if counters:
        COMMANDARGS.append('--counters')

    if modprobe is not None:
        COMMANDARGS.append('--modprobe')
        COMMANDARGS.append(modprobe)

    if table is not None:
        COMMANDARGS.append('--table')
        COMMANDARGS.append(table)

    INITCOMMAND = list(COMMANDARGS)
    INITCOMMAND.insert(0, bin_iptables_save)

    for chance in (1, 2):
        rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
        if stdout:
            initial_state = reformat(stdout, counters)
        elif initialize_from_null_state(bin_iptables, table=table):
            changed = True

    if not initial_state:
        module.fail_json(msg="Unable to initialize firewall from NULL state.")

    if state == 'saved':
        checksum_old, checksum_new = writein(path, initial_state)
        if checksum_new != checksum_old:
            changed = True

    if state != 'restored':
        cmd = ' '.join(INITCOMMAND)
        module.exit_json(changed=changed, cmd=cmd, initial_state=initial_state)

    #
    # All remaining code is for state=restored
    #
    b_path = to_bytes(path, errors='surrogate_or_strict')
    if not os.path.exists(b_path):
        module.fail_json(msg="Source %s not found" % (path))
    if not os.path.isfile(b_path):
        module.fail_json(msg="Source %s not a file" % (path))
    if not os.access(b_path, os.R_OK):
        module.fail_json(msg="Source %s not readable" % (path))

    MAINCOMMAND = list(COMMANDARGS)
    MAINCOMMAND.insert(0, bin_iptables_restore)

    if _back is not None:
        checksum_old, checksum_new = writein(_back, initial_state)
        if checksum_new != checksum_old:
            changed = True
        BACKCOMMAND = list(MAINCOMMAND)
        BACKCOMMAND.append(_back)

    if noflush:
        MAINCOMMAND.append('--noflush')

    MAINCOMMAND.append(path)
    cmd = ' '.join(MAINCOMMAND)

    TESTCOMMAND = list(MAINCOMMAND)
    TESTCOMMAND.insert(1, '--test')

    rc, stdout, stderr = module.run_command(TESTCOMMAND)
    if rc != 0:
        module.fail_json(msg="Source %s is not suitable for input to %s" % (path,
            os.path.basename(bin_iptables_restore)), rc=rc, stdout=stdout, stderr=stderr)

    rc, stdout, stderr = module.run_command(MAINCOMMAND, check_rc=True)
    rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
    restored_state = reformat(stdout, counters)
    if restored_state != initial_state:
        changed = True

    if _back is None:
        module.exit_json(
                applied=True,
                changed=changed,
                cmd=cmd,
                initial_state=initial_state,
                restored_state=restored_state)


    # The rollback implementation currently needs:
    # Here:
    # * test existence of the backup file, exit with success if it doesn't exist
    # * otherwise, restore iptables from this file and return failure
    # Action plugin:
    # * try to remove the backup file
    # * wait async task is finished and retrieve its final status
    # * modify it and return the result
    # Task:
    # * ansible_timeout set to the same value (or higher) than the timeout
    #   module param
    # * task attribute 'async' set to the same value (or higher) than the
    #   timeout module param
    # * task attribute 'poll' equals 0
    #
    for x in range(_timeout):
        if os.path.exists(_back):
            time.sleep(1)
            continue
        module.exit_json(
                applied=True,
                changed=changed,
                cmd=cmd,
                initial_state=initial_state,
                restored_state=restored_state)

    # Here we are: for whatever reason, but probably due to the current ruleset,
    # the action plugin (i.e. on the controller) was unable to remove the backup
    # cookie, so we restore initial state from it.
    rc, stdout, stderr = module.run_command(BACKCOMMAND, check_rc=True)
    rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
    backed_state = reformat(stdout, counters)

    os.remove(_back)

    module.fail_json(
            rollback_complete=(backed_state == initial_state),
            applied=False,
            cmd=cmd,
            msg="Failed to confirm state restored from %s. Firewall has been rolled back to initial state" % (path),
            initial_state=initial_state,
            restored_state=restored_state)


if __name__ == '__main__':
    main()
