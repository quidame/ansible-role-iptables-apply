iptables_apply
==============

Setup iptables firewall from scratch or on a per-rule basis.  A rollback
feature ensures the Ansible Controller will not be locked out of the target
host.

**SUMMARY**

- [Description](#description)
- [Requirements](#requirements)
- [Role Variables](#role-variables)
  - [Common Variables](#common-variables)
  - [Advanced Variables](#advanced-variables)
- [Template Variables](#template-variables)
  - [Common Templating](#common-templating)
  - [Advanced Templating](#advanced-templating)
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
- blind firewall sanitization by inserting a core of sanity rules *before*
  the current ones, that remain unchanged but may as well never be reached
  anymore.
- per-rule firewall management, allowing other roles to add or remove rules
  when installing or uninstalling services respectively.
- easy-to-write rules, with a list of dictionnaries with only two mandatory
  parameters.

Requirements
------------

Firewall management service (`iptables` or `netfilter-persistent`) must be
installed apart.

Role Variables
--------------

All variables used by the role are explicitly declared either in *defaults* or
in *vars* directories. Those declared in *vars* shouldn't be overridden in
almost all cases (and can't be overridden in *group_vars* or *host_vars*). So
this section is divided into two parts,
[Common Variables](#common-variables) and
[Advanced Variables](#advanced-variables)

Only a few variables control the behaviour of this role.
See [Template Variables](#template-variables) for variables applying to the
template provided by the role.

### Common Variables

* The action to perform when playing the role.  Defaults to `template`.  When
  the value is `append`, `insert` or `delete`, current iptables ruleset is the
  starting point, and `iptables_apply__rules` the rules to be appended,
  inserted or deleted.  Also note that like with the **iptables** module, the
  rules that already exist in a chain are not moved within this chain. But they
  can be updated if only one of their destination port(s) or comment string has
  changed.

  The action `flush` is also supported. It removes all rules and resets policy
  to *ACCEPT* for all chains of the tables listed in the variable
  `iptables_apply__flush_tables` (*filter* by default). This action makes that
  the service is *stopped* and *disabled*.

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

  Defaults to an empty list (`[]`). Example:

```yaml
iptables_apply__rules:
  - name: PostgreSQL
    dport: 5432
    #protocol: tcp
    #chain: INPUT
    #jump: ACCEPT
  - name: Knot DNS
    dport: 53,953
    protocol: udp
```

* The following variable defines the firewall's service name. As the
  implementation may vary a lot, only two services are currently supported:
  `iptables` for **Redhat** family, and `netfilter-persistent` for **Debian**
  family.  To be usable by the role, an alternative service must implement a
  `save` command. Default depends on the OS.

```yaml
iptables_apply__service: iptables
```

* This defines the delay, in seconds, after what the initial iptables ruleset
  is restored, if the applied one is not confirmed.

```yaml
iptables_apply__timeout: 20
```

### Advanced Variables

* Whether or not to make the currently applied ruleset persistent across
  reboots.

```yaml
iptables_apply__persist: true
```

* The two following variables are about firewall's service management.
  Running state defaults to `true`, activation state defaults to `true`.

```yaml
iptables_apply__service_enabled: true
iptables_apply__service_started: true
```

* The two following variables define the paths of two temporary files to create
  and work with, and then remove. There is absolutely no reason to modify their
  values.

```yaml
iptables_apply__path_backup: /run/iptables.saved
iptables_apply__path_buffer: /run/iptables.apply
```

Template Variables
------------------

The following variables refer to the template that comes with the role.  They
make sense as long as `iptables_apply__action`'s value is `template`.

All variables used by the role are explicitly declared either in *defaults* or
in *vars* directories. Those declared in *vars* shouldn't be overridden in
almost all cases (and can't be overridden in *group_vars* or *host_vars*). So
this section is divided into two parts,
[Common Templatings](#common-templating) and
[Advanced Templating](#advanced-templating)

### Common Templating

* This defines the path of a template file that once evaluated is used as input
  for the command `iptables-restore`.  Defaults to the template shipped with
  the role.

```yaml
iptables_apply__template: iptables_apply.j2
```

* The iptables rules to apply in addition to the sanity rules provided by the
  template.  This is a list of dictionnaries with the same keys than
  `iptables_apply__rules`, and defaults to the same value.

```yaml
iptables_apply__template_rules: "{{ iptables_apply__rules }}"
```

### Advanced Templating

* If `True`, current iptables ruleset is not flushed and rules from the template
  (the one shipped with the role) are **inserted** before the current ones. This
  variable is silently ignored if the current running state of iptables already
  contains `iptables_apply__template_mark`'s value, that makes it usable as a
  one-shot-option, avoiding to duplicate rules too much (thus, without modifying
  the playbook nor its commandline call).

```yaml
iptables_apply__template_noflush: false
```

* Whether or not to apply the core ruleset provided by the template. The core
  rules, a.k.a. sanity rules, are inserted to ensure they will be evaluated
  first even if `iptables_apply__template_noflush` is true.  Defaults to `true`.

```yaml
iptables_apply__template_core: true
```

* The default policy to apply for each chain of the filter table.  If a policy
  is undefined in this variable, then it will not be changed on the target. For
  example, to keep all current policies: `iptables_apply__template_policy: {}`

```yaml
iptables_apply__template_policy:
  input: DROP
  forward: DROP
  output: ACCEPT
```

* As the templating of a temporary file can't be idempotent, and as the
  templating of iptables is in itself very agressive, there must be a way to
  not replay the template action to not loose application rules appended
  between two plays. This is the purpose of this variable. Set it to `false`
  to force a replay.

```yaml
iptables_apply__template_once: true
```

* This variable defines a string that should be found in the `iptables-save`
  output to know/decide if the templated ruleset is already in use. Defaults
  to the rule dropping TCP packets in state NEW and not coming with only the
  `SYN` flag:

```yaml
iptables_apply__template_mark: '-A INPUT -p tcp -m tcp ! --tcp-flags FIN,SYN,RST,ACK SYN -m comment --comment "bad NEWs" -j DROP'
```

* This defines the path of an alternative template used to flush rules and
  reset policies to ACCEPT all packets. It is only effective when
  `iptables_apply__action` is set to `flush`.

```yaml
iptables_apply__flush: iptables_flush.j2
```

* This lists the tables to flush when evaluating `iptables_flush.j2`, i.e.
  either when
  `iptables_apply__action = flush` and
  `iptables_apply__flush = iptables_flush.j2`, or when
  `iptables_apply__template = iptables_flush.j2`.
  It accepts either a keyword (table name or `all`) or a list of these
  keywords. Defaults to `filter`.

```yaml
iptables_apply__flush_tables: filter
```

Dependencies
------------

None.

Example Playbook
----------------

Apply the core ruleset, ensuring a secure base setup with ssh access allowed
and no more.

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: iptables_apply
```

Apply the same ruleset on an already configured firewall you want to keep.

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: iptables_apply
      iptables_apply__template_noflush: yes
```

Apply core ruleset and some passing rules for monitoring tools.

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: iptables_apply
      iptables_apply__template_rules:
        - name: NRPE
          dport: 5666
        - name: SNMP
          dport: 161
        - name: SNMP
          dport: 161
          protocol: udp
```

Add a single and simple passing rule. Replace `append` by `delete` to remove it.

```yaml
---
- hosts: dns-servers
  become: yes
  roles:
    - role: iptables_apply
      iptables_apply__action: append
      iptables_apply__rules:
        - name: Knot DNS
          dport: 53,953
          protocol: udp
```

Do almost whatever you want, and bypass the rollback feature, by calling a
tasks file that uses ansible's `iptables` module. The action of the role
(`iptables_apply__action`) doesn't matter here, unless you explicitly map
rule's `action` and `state` to it.

```yaml
---
- hosts: db-servers
  become: yes
  tasks:
    - include_role:
        name: iptables_apply
        tasks_from: iptables.yml
  vars:
    iptables_apply__module_rules:
      - action: insert
        chain: INPUT
	protocol: tcp
	source_port: "1024:"
	destination_port: 5432
	ctstate: NEW
	syn: match
	comment: "postgresql.service"
        jump: ACCEPT
	state: present
```

Do whatever you want with a custom template. It may as well include policies
and rules for any table, not only the filter one.

```yaml
---
- hosts: routers
  become: yes
  roles:
    - role: iptables_apply
      iptables_apply__template: iptables/routers.j2
```

Manage persistence of the current ruleset:

```yaml
---
- hosts: all
  become: yes
  tasks:
    - include_role:
        name: iptables_apply
	tasks_from: iptables-persist.yml
```

Or manage the service (for example disable it and keep it started):

```yaml
---
- hosts: all
  become: yes
  tasks:
    - include_role:
        name: iptables_apply
	tasks_from: iptables-service.yml
      vars:
        iptables_apply__service_enabled: false
        iptables_apply__service_started: true
```

You may also want to play this role from another one (here, say from `foobar`):

```yaml
- include_role:
    name: iptables_apply
  vars:
    iptables_apply__action: "{{ 'append' if foobar__action == 'setup' else 'delete' }}"
    iptables_apply__rules:
      - name: FooBar over HTTP/HTTPS
        dport: "{{ foobar__http_port }},{{ foobar__https_port }}"
```

Install
-------

To make use of this role as a galaxy role, put the following lines in
`requirements.yml`:

```yaml
- name: iptables_apply
  src: https://github.com/quidame/ansible-role-iptables_apply.git
  version: 2.0.0
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
