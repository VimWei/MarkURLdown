# Changelog

## [1.0.7] - 2025-10-10

- feat: enhance appinn and nextjs handlers with new functionality
- Update screenshot asset with new version

## [1.0.6] - 2025-10-10

- feat: implement actual version check functionality

## [1.0.5] - 2025-10-09

- refactor: reorganize project structure and adjust UI

## [1.0.4] - 2025-10-09

- refactor: simplify logger usage
- refactor: update LOGGER_ARCHITECTURE_GUIDE.md and remove obsolete splitter design documents
- refactor: rename session to config and update storage paths

## [1.0.3] - 2025-10-09

- Enhance README.md: Update features and usage instructions for clarity and conciseness.
- Update license in README.md to GNU General Public License v3.0 (GPL-3.0) with detailed usage terms

## [1.0.2] - 2025-10-09

- chore: change license from MIT to GPL-3.0 in pyproject.toml
- feat(ConvertService): add translator support for human-readable duration formatting

## [1.0.1] - 2025-10-09

- refactor(ConvertService): improve shared browser handling and optimize test performance
- feat(BasicPage): enhance URL list management with multi-selection support

## [1.0.0] - 2025-10-08

- docs: update README
- chore(docs): update screenshots
- test: increase test coverage to 80% and strengthen critical cases
- fix(tests): resolve test failures after comprehensive GUI refactor
- refactor(config): unify session management and enhance configuration handling
- refactor(MainWindow): integrate ConfigService for session management
- refactor(gui): unify entry on MainWindow, remove legacy paths and StartupManager
- docs: add startup flow analysis document outlining GUI structure and responsibilities
- chore(docs): move Splitter analysis and design docs
- refactor(ui/basic): connect output directory change event to editingFinished signal
- feat(locales): enhance localization support and structured logging for conversion processes
- refactor(ui/basic): deterministic label/button widths on locale switch
- feat: Enhance progress bar with phase-aware interpolation and friendly labels
- UI: Replace dual Convert/Stop buttons with a single toggle
- fix(locales): update button label for consistency in English and Chinese
- fix(locales): update labels for clarity and consistency
- refactor(ui): remove unused log features; unify label styling
- fix(Advanced): open data/ correctly and show absolute path after Open
- feat: implement stop request handling in conversion processes
- feat: add duration tracking for conversion processes
- feat: implement structured logging system for conversion processes
- fix: update logging directory and suppress noisy logs during session import
- refactor: separate startup logic into services and utils layers
- refactor: implement layered configuration architecture
- feat: refactor configuration management architecture
- Delete temp test files
- fix: advanced page's config
- feat: implement multi-task logging functionality in GUI
- feat: implement direct logging system with simplified event handling
- Update integration and user acceptance tests for internationalization and performance
- Add detailed diagnostic and conversion testing scripts
- Implement GUI refactor phase 4 foundation: modular architecture framework
- Implement modular GUI refactor (Phase 1-3)
- Add design documents for GUI refactor plan
- Archive project_rename_guide.md

## [0.9.4] - 2025-10-03

- Fix: enforce UTF-8 encoding in subprocess command execution
- Improve test coverage to 80%

## [0.9.3] - 2025-10-03

- Update README for clarity and organization

## [0.9.2] - 2025-10-03

- Update splash screen assets and README

## [0.9.1] - 2025-10-03

- Update README and asset files

## [0.9.0] - 2025-10-03

- Rename more
- Rename MarkdownAll.vbs
- Rename tests/
- Rename files about release
- Rename docs/
- Rename src/markdownall/
- Rename project step 1-5

## [0.8.8] - 2025-10-02

- docs: add project rename guide for MarkURLdown to MarkdownAll

## [0.8.7] - 2025-10-02

- doc: update README and screenshot

## [0.8.6] - 2025-10-02

- feat(playwright): align shared-browser launch with standalone (Chrome + anti-detection flags)
- refactor(zhihu_handler): change browser launch mode to headless

## [0.8.5] - 2025-10-01

- feat(startup): add launch entry and improve splash handling
- feat(tests): add relative output_dir tests; improve handler coverage
- feat: store output_dir as project-relative path; resolve on load
- refactor: move user data directories under data/

## [0.8.4] - 2025-10-01

- fix(docs): update doc to reflect src structure

## [0.8.3] - 2025-10-01

- refactor(docs): migrate documentation to new src structure and update handler paths

## [0.8.2] - 2025-10-01

- doc: Update screenshot

## [0.8.1] - 2025-10-01

- chore: update VBScript launcher and README

## [0.8.0] - 2025-10-01

- refactor(tests): update test coverage commands and streamline version checks
- test(tests): enhance app title tests for version formatting
- fix: update test command and improve UI localization
- feat(src): complete migration to src layout with markurldown package

## [0.7.3] - 2025-10-01

- feat(tests): raise coverage from 19% to 75%

## [0.7.2] - 2025-09-30

- docs: update SRC migration plan with detailed steps and new directory structure
- docs: plan migration to src layout (src/markurldown) and console entry

## [0.7.1] - 2025-09-30

- ci: accept English or Chinese changelog header

## [0.7.0] - 2025-09-30

- feat: add automated release and version management system

## [0.6.0] - 2025-09-30

### Added
- Establish comprehensive testing framework
- Add handler test coverage
- Add integration test support
- Improve testing infrastructure

### Changed
- Enhance code quality and stability
- Increase test coverage

## [0.5.0] - 2025-09-30

### Added
- Initial stable release
- Core functionality implementation
- Basic handler support
- User interface improvements

