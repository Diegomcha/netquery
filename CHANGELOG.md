# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0b2] - 2025-06-26

### Added
- **Introduced a new CLI tool**: `netquery-convert`, which transforms `netquery` CSV output into structured JSON input. Supports customizable grouping and labeling of devices.
- Added a **`--version`** flag to both `netquery` and `netquery-convert` for dynamic version display.

### Changed
- Enhanced `netquery` to support **multiple machine definition files**.
- **Updated regex filtering behavior**: now uses the full match instead of the first capturing group. Users should use lookbehind/lookahead for more precise filtering.
- Output tables now include a **`File` column** when multiple machine files are provided.
- **Improved JSON output** formatting for better compatibility and readability.
- Refined CLI prompts and help messages for a clearer user experience.

## [1.0.0b1] - 2025-06-19
