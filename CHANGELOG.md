# iptables_apply

## [4.1.1] 2020-02-03
### Fixed
- 'ansible-test sanity' errors

### Added
- module's DOCUMENTATION.requirements
- vim fold markers in playbook test.yml

## [4.1.0] 2020-01-20
### Added
- Role assertions (ansible and OS compatibility)
- Test cases about rollbacks, playing with timeouts and DROP or REJECT.

### Changed
- Convert loop `while` -> `for` based on the timeout to retrieve async result.
- Move `async_dir` search/compute above and use it to build the path of the
  temporary backup/cookie.
- Remove internal params from results when not used.
- Use ansible way to write into the destination file.
- Use bytes when interacting with filesystem.
- Rewrite template for better output formats.


## [4.0.0] 2020-01-10
### Added
- Action plugin `iptables_state`: manage the connection reset and the rollback
  on its own.

### Changed
- Remove tasks now covered by the module (or the action plugin) and refactor
  all others consequently.
- Update tests.

## [3.0.0]
### Added
- Ad hoc module `iptables_state` to manage saving and restoring iptables state
  to/from a file

### Changed
- Rename `iptables_apply__timeout` to `iptables_apply__rollback_timeout`
- Refactor tasks to use the embedded module
- Update tests playbook

### Removed
- Remove templated shell script, no more needed

## [2.0.0]
### Changed
- Rename `iptables_apply__noflush` to `iptables_apply__template_noflush`
- Move all role variables from `vars` to `defaults`
- Update README accordingly

## [1.5.1] 2019-12-29
### Fixed
- idempotency issue with quoted comments

### Changed
- put shell templated commands into a dedicated file

### Added
- this changelog

## [1.5.0] 2019-12-19
### Added
- support for nft (iptables-nft)

## [1.4.0] 2019-05-19
### Changed
- replace connection plugin switch by reset_connection
- rewrite tests

## [1.3.0] 2019-01-15
### Changed
- rewrite tests

## [1.2.2] 2019-01-08
### Fixed
- scalability issue
- iptables state initialization

## [1.2.1] 2019-01-07
### Fixed
- ansible-lint 4.0.1

## [1.2.0] 2019-01-06
### Changed
- revert to connection plugin switch (remove *meta: reset_connetion*

## [1.1.0] 2019-01-04
### Fixed
- scalability (remove `wait_for_connection`)

### Changed
- rewrite test playbook

## [1.0.0] 2019-01-03
### Changed
- replace connection plugin switch by a *meta* `reset_connection`
- number inserted rules instead of reverting the order
- bump min_ansible_verion to 2.5

### Added
- action `flush`
- option *--noflush* for `template` action
- enhance documentation
- playbook for tests

## [0.4.0] 2018-12-31
### Added
- 3 variables for service management
- improve documentation

## [0.3.0] 2018-12-30
### Added
- per-rule management

## [0.2.0] 2018-12-20
### Added
- save iptables state
- manage iptables service

## [0.1.0] 2018-12-06
init role
