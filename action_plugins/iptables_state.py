# (c) 2020, quidame <quidame@poivron.org>
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time

from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash
from ansible.utils.display import Display
from ansible.errors import AnsibleError, AnsibleActionFail, AnsibleConnectionFailure

display = Display()


class ActionModule(ActionBase):

    # Default values of the module params:
    DEFAULT_PATH = None
    DEFAULT_BACK = None
    DEFAULT_STATE = None
    DEFAULT_TABLE = None
    DEFAULT_TIMEOUT = 20
    DEFAULT_NOFLUSH = False
    DEFAULT_COUNTERS = False
    DEFAULT_MODPROBE = None
    DEFAULT_IP_VERSION = 'ipv4'

    DEFAULT_SUDOABLE = True

    def run(self, tmp=None, task_vars=None):

        # individual modules might disagree but as the generic the action plugin, pass at this point.
        self._supports_check_mode = False
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        task_async = self._task.async_val
        task_poll = self._task.poll
        module_name = self._task.action
        module_args = self._task.args
        module_opts = dict(
                path = module_args.get('path', self.DEFAULT_PATH),
                back = module_args.get('back', self.DEFAULT_BACK),
                state = module_args.get('state', self.DEFAULT_STATE),
                table = module_args.get('table', self.DEFAULT_TABLE),
                timeout = module_args.get('timeout', self.DEFAULT_TIMEOUT),
                noflush = module_args.get('noflush', self.DEFAULT_NOFLUSH),
                counters = module_args.get('counters', self.DEFAULT_COUNTERS),
                modprobe = module_args.get('modprobe', self.DEFAULT_MODPROBE),
                ip_version = module_args.get('ip_version', self.DEFAULT_IP_VERSION),
        )


        if not result.get('skipped'):

            if result.get('invocation', {}).get('module_args'):
                # avoid passing to modules in case of no_log
                # should not be set anymore but here for backwards compatibility
                del result['invocation']['module_args']

            # FUTURE: better to let _execute_module calculate this internally?
            wrap_async = self._task.async_val and not self._connection.has_native_async

            # do work!
            result = merge_hash(result, self._execute_module(task_vars=task_vars, wrap_async=wrap_async))

            if self._task.args.get('state', None) == 'restored':
                try:
                    self._connection.reset()
                    display.v("%s: reset connection" % (self._task.action))
                except AttributeError:
                    display.warning("Connection plugin does not allow to reset the connection")

        if not wrap_async:
            # remove a temporary path we created
            self._remove_tmp_path(self._connection._shell.tmpdir)

        return result
