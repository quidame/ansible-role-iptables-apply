# (c) 2020, quidame <quidame@poivron.org>
# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time

from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash
from ansible.errors import AnsibleError, AnsibleActionFail, AnsibleConnectionFailure


class ActionModule(ActionBase):

    _VALID_ARGS = frozenset(('path', 'state', 'table', 'noflush', 'counters', 'modprobe', 'ip_version'))
    DEFAULT_SUDOABLE = True

    MSG_ERROR__ASYNC_AND_POLL_NOT_ZERO = (
            "This module doesn't support async>0 and poll>0 when its 'state' param "
            "is set to 'restored'. To enable its rollback feature (that needs the "
            "module to run asynchronously on the remote), please set task attribute "
            "'poll' to 0, and 'async' to a value not greater than 'ansible_timeout' "
            "(recommended, not checked).")
    MSG_WARNING__NO_ASYNC_IS_NO_ROLLBACK = (
            "Attempts to restore iptables state without rollback in case of mistake "
            "may lead the ansible controller to loose access to the hosts and never "
            "regain it before fixing firewall rules through a serial console, or any "
            "other way except SSH. Please set task attribute 'poll' to 0, and 'async' "
            "to a value not greater than 'ansible_timeout' (recommended, not checked).")


    # Retrieve results of the asynchonous task, and display them in place of
    # the async wrapper results (those with the ansible_job_id key).
    def _async_result(self, module_name, module_args, task_vars):
        async_result = {}
        async_result['finished'] = 0

        while async_result['finished'] == 0:
            async_result = self._execute_module(
                    module_name=module_name,
                    module_args=module_args,
                    task_vars=task_vars,
                    wrap_async=False)

        del async_result['ansible_job_id']
        del async_result['finished']

        if 'restored_state' in async_result:
            if async_result['restored_state'] == async_result['initial_state']:
                async_result['changed'] = False

        return async_result


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


        if not result.get('skipped'):

            if result.get('invocation', {}).get('module_args'):
                # avoid passing to modules in case of no_log
                # should not be set anymore but here for backwards compatibility
                del result['invocation']['module_args']

            # FUTURE: better to let _execute_module calculate this internally?
            wrap_async = self._task.async_val and not self._connection.has_native_async

            if 'state' in module_args and module_args['state'] == 'restored':
                if not task_async:
                    self._display.warning(self.MSG_WARNING__NO_ASYNC_IS_NO_ROLLBACK)
                elif task_poll:
                    raise AnsibleActionFail(self.MSG_ERROR__ASYNC_AND_POLL_NOT_ZERO)
                else:
                    # Bind the loop max duration to the same value on both
                    # remote and local sides, and set a backup file path.
                    module_args['_timeout'] = task_async
                    module_args['_back'] = '/run/iptables.state'

            # do work!
            result = merge_hash(result, self._execute_module(module_args=module_args, task_vars=task_vars, wrap_async=wrap_async))

            # Then the 3-steps "go ahead or rollback":
            # - reset connection to ensure a persistent one will not be reused
            # - confirm the restored state by removing the backup on the remote
            # - retrieve the results of the asynchronous task to return them
            if '_back' in module_args:
                try:
                    self._connection.reset()
                    self._display.v("%s: reset connection" % (module_name))
                except AttributeError:
                    self._display.warning("Connection plugin does not allow to reset the connection.")

                confirm_cmd = 'rm %s' % module_args['_back']
                for x in range(int(module_args['_timeout'])):
                    time.sleep(1)
                    # It is expected that the host may be unreachable. We don't
                    # want to fail for that, since we can wait for the rollback
                    # to happen, to access to the host again.
                    # - AnsibleConnectionFailure covers rejected requests (i.e.
                    #   by rules with '--jump REJECT')
                    # - ansible_timeout is able to cover dropped requests (due
                    #   to a rule or policy DROP) if not lower than async_val.
                    try:
                        confirm_res = self._low_level_execute_command(confirm_cmd, sudoable=self.DEFAULT_SUDOABLE)
                        break
                    except AnsibleConnectionFailure:
                        continue


                async_status_args = {}
                async_status_args['jid'] = result['ansible_job_id']

                # BEGIN snippet from async_status action plugin
                env_async_dir = [e for e in self._task.environment if
                                 "ANSIBLE_ASYNC_DIR" in e]
                if len(env_async_dir) > 0:
                    # for backwards compatibility we need to get the dir from
                    # ANSIBLE_ASYNC_DIR that is defined in the environment. This is
                    # deprecated and will be removed in favour of shell options
                    async_dir = env_async_dir[0]['ANSIBLE_ASYNC_DIR']

                    msg = "Setting the async dir from the environment keyword " \
                          "ANSIBLE_ASYNC_DIR is deprecated. Set the async_dir " \
                          "shell option instead"
                    self._display.deprecated(msg, "2.12")
                else:
                    # inject the async directory based on the shell option into the
                    # module args
                    async_dir = self.get_shell_option('async_dir', default="~/.ansible_async")
                ### END snippet from async_status action plugin

                async_status_args['_async_dir'] = async_dir
                result = self._async_result('async_status', async_status_args, task_vars)

                async_status_args['mode'] = 'cleanup'
                garbage = self._execute_module(
                        module_name='async_status',
                        module_args=async_status_args,
                        task_vars=task_vars,
                        wrap_async=False)

        # remove a temporary path we created
        self._remove_tmp_path(self._connection._shell.tmpdir)

        return result
