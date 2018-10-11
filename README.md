iptables-apply
==============

Setup the firewall with a core iptables ruleset and application-specific rules
that will replace the current setup. A rollback feature ensures you will not be
locked out the target host.

Requirements
------------

None.

Role Variables
--------------

```yaml
iptables_apply__noflush: false
```
If `True`, current iptables ruleset is not flushed and rules from the template
are inserted.

```yaml
iptables_apply__template: "iptables.j2"
```
This defines the path of a template file that once evaluated is used as input
for the command `iptables-restore`.

```yaml
iptables_apply__timeout: 20
```
It defines the delay, in seconds, after what the initial iptables ruleset is
restored.

Dependencies
------------

None.

Example Playbook
----------------

```yaml
- hosts: servers
  roles:
    - role: iptables-apply
```

License
-------

GPLv3

Author Information
------------------

<quidame@poivron.org>
