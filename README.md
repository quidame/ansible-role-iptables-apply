iptables_apply
==============

Setup iptables firewall from a template. A rollback feature ensures the Ansible
Controller will not be locked out the target host.

**SUMMARY**

- [Description](#description)
- [Requirements](#requirements)
- [Role Variables](#role-variables)
- [Dependencies](#dependencies)
- [Example Playbook](#example-playbook)
- [Galaxy](#galaxy)
- [License](#license)
- [Author Information](#author-information)


Description
-----------

This role populates target's iptables ruleset from a template, also flushing
(the default) or keeping existing rules. If the next task fails, meaning that
the target is not reachable anymore, the firewall is restarted with its initial
configuration, so the ansible controller, at least, is not locked out of its
target.

Requirements
------------

Both `ssh` and `paramiko` clients must be supported by the controller. This
role doesn't work in *Cygwin* environment.

Role Variables
--------------

Only a few variables control the behaviour of this role. The most important of
them is the template file.

* If `True`, current iptables ruleset is not flushed and rules from the template
  are **inserted** before the current ones.

```yaml
iptables_apply__noflush: false
```

* Whether or not to make the currently applied ruleset persistent across
  reboots.

```yaml
iptables_apply__save_state: true
```

* This defines the path of a template file that once evaluated is used as input
  for the command `iptables-restore`.

```yaml
iptables_apply__template: "iptables_apply.j2"
```

* This defines the delay, in seconds, after what the initial iptables ruleset
  is restored.

```yaml
iptables_apply__timeout: 20
```

Dependencies
------------

None.

Example Playbook
----------------

Apply the core ruleset, ensuring a secure base setup with ssh access allowed
and no more.

```yaml
- hosts: servers
  roles:
    - role: iptables_apply
```

Apply the same ruleset on an already configured firewall you want to keep.

```yaml
- hosts: servers
  roles:
    - role: iptables_apply
      iptables_apply__noflush: yes
```

Galaxy
------

To make use of this role as a galaxy role, put the following lines in
`requirements.yml`:

```yaml
- name: iptables_apply
  src: https://github.com/quidame/ansible-role-iptables_apply.git
  version: 0.2.0
  scm: git
```

and then

```bash
ansible-galaxy install -r requirements.yml
```

License
-------

GPLv3

Author Information
------------------

<quidame@poivron.org>
