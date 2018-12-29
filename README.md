iptables_apply
==============

Setup iptables firewall from scratch or on a per-rule basis.  A rollback
feature ensures the Ansible Controller will not be locked out of the target
host.

**SUMMARY**

- [Description](#description)
- [Requirements](#requirements)
- [Role Variables](#role-variables)
- [Template Variables](#template-variables)
- [Dependencies](#dependencies)
- [Example Playbook](#example-playbook)
- [Galaxy](#galaxy)
- [License](#license)
- [Author Information](#author-information)


Description
-----------

This role populates target's iptables ruleset from a template, also flushing
(the default) or keeping existing rules; or modifies current ruleset by adding
or removing service-specific rules.  If the next task fails, meaning that the
target is not reachable anymore, the firewall is restarted with its initial
configuration, so the ansible controller, at least, is not locked out of its
target.

This role comes with the following features:

- rollback in case of failure
- full firewall configuration from scratch
- blind firewall sanitization by inserting a core of sanity rules  *before*
  the current ones, that remain unchanged but may as well never be reached
  anymore.
- per-rule firewall management, allowing other roles to add or remove rules
  when installing or uninstalling services respectively.
- easy-to-write rules, with a list of dictionnaries with only two mandatory
  parameters.

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
iptables_apply__persist: true
```

* This defines the delay, in seconds, after what the initial iptables ruleset
  is restored.

```yaml
iptables_apply__timeout: 20
```

Template Variables
------------------

The following variables refer to the template that comes with the role.  They
make sense as long as `iptables_apply__action`'s value is `template`.

* This defines the path of a template file that once evaluated is used as input
  for the command `iptables-restore`.  Defaults to the template shipped with
  the role.

```yaml
iptables_apply__template: iptables_apply.j2
```

* Whether or not to apply the core ruleset provided by the template. The core
  rules, a.k.a. sanity rules, are inserted to ensure they will be evaluated
  first even if `iptables_apply__noflush` is true.  Defaults to `true`.

```yaml
iptables_apply__template_core: true
```

* The default policy to apply for each chain of the filter table.  If a policy
  is undefined in this variable, then it will not be changed on the target. For
  example, to keep all current policies (useful with `iptables_apply__noflush`
  set to `True`): `iptables_apply__template_policy: {}`

```yaml
iptables_apply__template_policy:
  input: DROP
  forward: DROP
  output: ACCEPT
```

* The iptables rules to apply in addition to the sanity rules provided by the
  template.  This is a list of dictionnaries with the same keys than
  `iptables_apply__rules`, and defaults to the same value.

```yaml
iptables_apply__template_rules: "{{ iptables_apply__rules }}"
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
