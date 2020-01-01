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
    default: saved
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
    default; false
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
    type: str
  path:
    description:
      - The file the iptables state should be saved to.
      - The file the iptables state should be restored from.
      - Required when I(state=saved) or I(state=restored).
    type: path
  back:
    description:
      - The file the iptables state should be rolled back from.
      - The file is removed in case of successfull rollback.
    type: path
  timeout:
    description:
      - The time in seconds after what the rollback happens if new ruleset is
        not confirmed (based on existence of the backup file).
    type: int
    default: 20
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
    path: /etc/sysconfig/iptables.alt


# This sequence (3 tasks) implements a rollback in case of big mistake. Note
# that the `async` value MUST be greater or equal to the `timeout` parameter.
- name: "1. apply ruleset and wait for confirmation"
  iptables_state:
    state: restored
    path: /run/iptables.apply
    back: /run/iptables.saved
    timeout: "{{ iptables_state_timeout }}"
  async: "{{ iptables_state_timeout }}"
  poll: 0

- meta: reset_connection

- name: "2. confirm applied ruleset to avoid rollback"
  file:
    path: /run/iptables.saved
    state: absent
  register: confirm
  failed_when: confirm is not changed
'''

RETURN = r'''
initial_state:
    description: the current state of the firewall when module starts
    type: list
    returned: success
restored_state:
    description: the new state of the firewall, when state=restored
    type: list
    returned: success
'''


import re
import os
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes


SAVE = dict(
    ipv4='iptables-save',
    ipv6='ip6tables-save',
)

RESTORE = dict(
    ipv4='iptables-restore',
    ipv6='ip6tables-restore',
)


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
            ip_version=dict(type='str', default='ipv4', choices=['ipv4', 'ipv6']),
            path=dict(type='path'),
            back=dict(type='path'),
            state=dict(type='str', choices=['saved', 'restored']),
            table=dict(type='str', choices=['filter', 'nat', 'mangle', 'raw', 'security']),
            timeout=dict(type='int', default=20),
            noflush=dict(type='bool', default=False),
            counters=dict(type='bool', default=False),
            modprobe=dict(type='path'),
        ),
        required_together=[
            ['state', 'path'],
        ],
    )

    args = dict(
        ip_version = module.params['ip_version'],
        path = module.params['path'],
        back = module.params['back'],
        state = module.params['state'],
        table = module.params['table'],
        timeout = module.params['timeout'],
        noflush = module.params['noflush'],
        counters = module.params['counters'],
        modprobe = module.params['modprobe'],
    )


    bin_iptables_save = module.get_bin_path(SAVE[args['ip_version']], True)
    bin_iptables_restore = module.get_bin_path(RESTORE[args['ip_version']], True)

    os.umask(0o077)
    changed = False
    COMMANDARGS = []

    if args['counters']:
        COMMANDARGS.append('--counters')

    if args['modprobe'] is not None:
        COMMANDARGS.append('--modprobe')
        COMMANDARGS.append(args['modprobe'])

    if args['table'] is not None:
        COMMANDARGS.append('--table')
        COMMANDARGS.append(args['table'])

    INITCOMMAND = list(COMMANDARGS)
    INITCOMMAND.insert(0, bin_iptables_save)

    rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
    initial_state = reformat(stdout, args['counters'])

    if args['state'] == 'saved':
        checksum_old, checksum_new = writein(args['path'], initial_state)
        if checksum_new != checksum_old:
            changed = True

    if args['state'] != 'restored':
        cmd = ' '.join(INITCOMMAND)
        module.exit_json(changed=changed, cmd=cmd, initial_state=initial_state)

    #
    # All remaining code is for state=restored
    #
    b_path = to_bytes(args['path'], errors='surrogate_or_strict')
    if not os.path.exists(b_path):
        module.fail_json(msg="Source %s not found" % (args['path']))
    if not os.path.isfile(b_path):
        module.fail_json(msg="Source %s not a file" % (args['path']))
    if not os.access(b_path, os.R_OK):
        module.fail_json(msg="Source %s not readable" % (args['path']))

    MAINCOMMAND = list(COMMANDARGS)
    MAINCOMMAND.insert(0, bin_iptables_restore)

    if args['back'] is not None:
        checksum_old, checksum_new = writein(args['back'], initial_state)
        if checksum_new != checksum_old:
            changed = True
        BACKCOMMAND = list(MAINCOMMAND)
        BACKCOMMAND.append(args['back'])

    if args['noflush']:
        MAINCOMMAND.append('--noflush')

    MAINCOMMAND.append(args['path'])
    cmd = ' '.join(MAINCOMMAND)

    TESTCOMMAND = list(MAINCOMMAND)
    TESTCOMMAND.insert(1, '--test')

    rc, stdout, stderr = module.run_command(TESTCOMMAND)
    if rc != 0:
        module.fail_json(msg="Source %s is not suitable for input to %s" % (args['path'],
            os.path.basename(bin_iptables_restore)), rc=rc, stdout=stdout, stderr=stderr)

    rc, stdout, stderr = module.run_command(MAINCOMMAND, check_rc=True)
    rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
    restored_state = reformat(stdout, args['counters'])
    if restored_state != initial_state:
        changed = True

    if args['back'] is None:
        module.exit_json(changed=changed, cmd=cmd, initial_state=initial_state, restored_state=restored_state)

    # The poorly implemented rollback here (an action plugin, as for reboot,
    # that even embeds the reset_connection, would be much better). Remember
    # that to make it working as expected, it needs:
    # - 3 tasks
    #   * call this module
    #   * reset connection
    #   * remove the backup
    # - The first task must be called with
    #   * async set to the same value (or higher) than the timeout module param
    #   * poll=0
    #
    for x in range(args['timeout']):
        if os.path.exists(args['back']):
            time.sleep(1)
            continue
        module.exit_json(changed=changed, cmd=cmd, initial_state=initial_state, restored_state=restored_state)

    rc, stdout, stderr = module.run_command(BACKCOMMAND, check_rc=True)
    rc, stdout, stderr = module.run_command(INITCOMMAND, check_rc=True)
    backed_state = reformat(stdout, args['counters'])

    os.remove(args['back'])

    module.fail_json(msg="Failed to confirm state restored from %s" % (args['path']))


if __name__ == '__main__':
    main()
