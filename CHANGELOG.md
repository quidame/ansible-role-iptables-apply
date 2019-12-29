# iptables_apply

## [1.5.1] 2019-12-29
### Fixed
- idempotency issue with quoted comments

### Changed
- put shell templated commands into a dedicated file

### Added
- this changelog

## [1.5.0] 2019-12-19
### Added
- support for nft (iptables-nft

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
