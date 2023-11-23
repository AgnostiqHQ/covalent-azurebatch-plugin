# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### Changed

- Required terraform version to ">= 1.6"
- Use `templatefile` instead of `data "template_file` ...

## [0.16.0] - 2023-11-21

### Changed

- Changed `application_id` to `client_id` since `application_id` is being deprecated
- Changed `plugin_defaults` & `infra_defaults` to pydantic models

### Added

- Added tftpl file for generating conf file
- Added script in the main.tf for conf template

## [0.15.0] - 2023-11-21

### Changed

- Changed the README.md banner from default covalent jpg to azure batch's svg file

## [0.14.0] - 2023-09-21

### Changed

- Changed license to Apache

## [0.13.0] - 2023-09-20

### Changed

- Updated Terraform version

## [0.12.0] - 2023-06-07

### Added

- Terraform scripts to deploy and use these resources

### Fixed

- PipDeps now work

## [0.11.0] - 2022-12-14

### Changed

- Make Covalent Base Executor image configurable via environment variables.

## [0.10.0] - 2022-12-08

### Changed

- Boilerplate detail.

## [0.9.0] - 2022-12-07

### Added

- Functional tests scripts.

## [0.8.0] - 2022-12-06

### Added

- Configuration and required Azure resources section in the README. 

## [0.7.0] - 2022-11-25

### Fixed 

- Changed client arguments from `credentials` to `credential` for blob storage client.

### Added 

- Implementation of submit_task and cancel methods.
- Unit tests for the corresponding methods.
- Unit test to ensure that environment variable setting exceptions are being raised.

### Changed
- Storage account domain name is read from the executor attributes instead of being hardcoded.

## [0.6.0] - 2022-11-17

### Added 

- Implementation of upload_task, get_status and query_result methods.
- Unit tests for the corresponding methods above.
- Codecov token in tests.yml. Needs to be taken out before this repo becomes public. 

## [0.5.0] - 2022-11-16

### Added

- Added base executor Dockerfile 

## [0.4.0] - 2022-11-14

### Added

- Implementation of run, validate_credential, debug_log and poll task methods.
- Implementation of corresponding unit tests.

## [0.3.0] - 2022-11-08

### Fixed

- Changelog workflow.
- Attempt to fix non-linear commit history by rebasing onto develop

### Changed

- Updated `placeholder_test` to `test_validate_credentials`

### Operations

- Added CI workflows.

## [0.2.0] - 2022-11-04

### Added

- Skeleton for Azure Batch.

## [0.1.0] - 2022-11-04

### Added

- Basic setup for Covalent Azure batch repo.
