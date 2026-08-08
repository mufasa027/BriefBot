# Changelog

All notable changes to CipherBrief will be documented in this file.

## [1.0.0] - 2026-08-07

### Added
- **Production Stabilization**: Complete audit and resolution of all P0 bugs.
- **Concurrency Safety**: Implemented `try...finally` database connection management and SQLite atomic upserts.
- **DevEx Suite**: Added Dockerfile, docker-compose, Makefile, and GitHub Actions CI pipelines.
- **Documentation**: Professional README, Architecture docs, and Contribution guidelines.
- **Testing Foundation**: Pytest suite covering ranking, editorial, and clustering logic.

### Changed
- Refactored project name references to consistently use `CipherBrief`.
- Pinned `requirements.txt` to exact versions for reproducible builds.

### Removed
- Dead code artifacts, legacy image generators, and debug dumps (`structure.txt`, `tree.txt`).
