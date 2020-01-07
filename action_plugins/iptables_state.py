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

    DEFAULT_SUDOABLE = True

    # I'm unable to override async_val AND poll values from here. So... just
    # fail if they don't match the required values.
    def _async_is_needed(self, module_name, module_timeout, task_async, task_poll, task_vars):
        msg = ('Task attribute \'async\' (= %s) MUST be set to a value greater than or equal to '
               '\'timeout\' module parameter (currently %s), and attribute \'poll\' (= %s) MUST '
               'be set to 0, to enable rollback feature. This is also the case for the more global '
               '\'ansible_timeout\' (= %s), which has to be greater or equal to the module param.'
               % (task_async, module_timeout, task_poll, task_vars['ansible_timeout']))

        if task_async < module_timeout or task_poll != 0:
            raise AnsibleActionFail(msg)
        else:
            display.v("%s: run in background until completed or for max %s seconds." % (module_name, module_timeout))
            return True


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

            if module_args['state'] == 'restored':
                self._async_is_needed(
                        module_name,
                        int(module_args['timeout']),
                        int(task_async),
                        int(task_poll),
                        task_vars)

            # do work!
            result = merge_hash(result, self._execute_module(task_vars=task_vars, wrap_async=wrap_async))

            # Then the 3-steps "go ahead or rollback":
            # - reset connection to ensure a persistent one will not be reused
            # - confirm the restored state by removing the backup/cookie
            # - retrieve results of the asynchronous task to return them
            if module_args['state'] == 'restored':
                try:
                    self._connection.reset()
                    display.v("%s: reset connection" % (module_name))
                except AttributeError:
                    display.warning("Connection plugin does not allow to reset the connection")

                confirmation_command = 'rm %s' % module_args['back']
                for x in range(int(module_args['timeout'])):
                    time.sleep(1)
                    try:
                        confirmation = self._low_level_execute_command(confirmation_command, sudoable=self.DEFAULT_SUDOABLE)
                        break
                    except AnsibleConnectionFailure:
                        continue


                async_status_args = {}
                async_status_args['jid'] = result['ansible_job_id']

                ### Begin Ansible 2.7 -> 2.8 compatibility stuff {{{
                set_async_dir = True
                try:
                    opt_async_dir = self.get_shell_option('async_dir', default="~/.ansible_async")
                except AttributeError:
                    set_async_dir = False

                if set_async_dir:
                    env_async_dir = [e for e in self._task.environment if "ANSIBLE_ASYNC_DIR" in e]
                    if len(env_async_dir) > 0:
                        async_dir = env_async_dir[0]['ANSIBLE_ASYNC_DIR']
                    else:
                        async_dir = opt_async_dir

                    async_status_args['_async_dir'] = async_dir
                ##### End Ansible 2.7 -> 2.8 compatibility stuff }}}

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
