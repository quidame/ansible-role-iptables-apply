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
- [Install](#install)
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

Only a few variables control the behaviour of this role.
See [Template Variables](#template-variables) for variables applying to the
template provided by the role.

* The action to perform when playing the role.  Defaults to `template`.  When
  the value is `append`, `insert` or `delete`, current iptables ruleset is the
  starting point, and `iptables_apply__rules` the rules to be appended,
  inserted or deleted.  Also note that like with the **iptables** module, the
  rules that already exist in a chain are not moved within this chain.

```yaml
iptables_apply__action: template
```

* The iptables rules to `append`/`insert` to, or to `delete` from the current
  rules, depending on `iptables_apply__action` value.  This is a list of
  dictionnaries accepting the following keys:

  | key | mandatory | type | choices | default | description |
  | :-- | :-------- | :--- | :------ | :------ | :---------- |
  | `chain` | no | keyword | `INPUT`, `FORWARD`, `OUTPUT` | `INPUT` | The chain the rule will be added to. |
  | `dport` | yes | string or integer ||| Port number, port range, or comma-separated list of port numbers and port ranges. |
  | `jump` | no | keyword | `ACCEPT`, `DROP`, `REJECT` | `ACCEPT` | What to do with packets matching the rule. |
  | `name` | yes | string ||| Used as the rule's comment. |
  | `protocol` | no | keyword | `tcp`, `udp` | `tcp` | The protocol packets have to match. |

  Defaults to an empty list (`[]`)

```yaml
iptables_apply__rules:
  - name: PostgreSQL
    dport: 5432
  - name: Knot DNS
    dport: 53,953
    protocol: udp
```

* If `True`, current iptables ruleset is not flushed and rules from the template
  (the one shipped with the role) are **inserted** before the current ones. This
  value should not be changed unless `iptables_apply__action` is `template`.

```yaml
iptables_apply__noflush: false
```

* Whether or not to make the currently applied ruleset persistent across
  reboots.

```yaml
iptables_apply__persist: true
```

* The three following variables are about firewall's service management. As the
  implementation may vary a lot, only two services are currently supported:
  `iptables` for **Redhat** family, and `netfilter-persistent` for **Debian**
  family.  To be usable by the role, an alternative service must implement a
  `save` command. For the service name, the default value depends on the OS; for
  its running state and activation state, defaults are `true` and `true`.

```yaml
iptables_apply__service: iptables
iptables_apply__service_enabled: true
iptables_apply__service_started: true
```

* This defines the delay, in seconds, after what the initial iptables ruleset
  is restored, if not confirmed.

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

Add a single passing rule.  Replace `append` by `delete` to remove it.

```yaml
- hosts: dns-servers
  roles:
    - role: iptables_apply
      iptables_apply__action: append
      iptables_apply__rules:
        - name: Knot DNS
          dport: 53,953
          protocol: udp
```

Flush rules and reset policies, but keep firewall running and enabled.

```yaml
- hosts: all
  roles:
    - role: iptables_apply
      iptables_apply__template_core: no
      iptables_apply__template_rules: []
      iptables_apply__template_policy:
        input: ACCEPT
        forward: ACCEPT
        output: ACCEPT
```

Install
-------

To make use of this role as a galaxy role, put the following lines in
`requirements.yml`:

```yaml
- name: iptables_apply
  src: https://github.com/quidame/ansible-role-iptables_apply.git
  version: 0.3.0
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
