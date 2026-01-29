# GeoDataCheck - Requirements Specification

**Project**: Geo Data Validation Tool for BBL
**Organization**: Bundesamt für Bauten und Logistik (BBL), Switzerland
**Version**: 1.0 Draft
**Date**: January 2026

---

## 1. Executive Summary

GeoDataCheck is an internal web application for validating spatial data in real estate portfolio datasets. Users upload Excel files containing addresses, coordinates, and Swiss building identifiers (EGIDs). The system runs configurable Python-based validation rules and provides immediate feedback through a dashboard and downloadable reports.

**Key Principle**: No data is stored on the server. Files are processed in-memory and immediately discarded to ensure data compliance.

---

## 2. Functional Requirements

### 2.1 File Upload

| ID | Requirement | Priority |
|----|-------------|----------|
| F-UP-01 | Users can upload Excel files (.xlsx, .xls) via drag-and-drop or file picker | Must |
| F-UP-02 | System validates file format before processing | Must |
| F-UP-03 | Maximum file size limit configurable (default: 50MB) | Must |
| F-UP-04 | Support for multiple sheets within a workbook | Should |
| F-UP-05 | Column mapping interface if headers don't match expected schema | Should |
| F-UP-06 | Preview of first N rows before validation | Should |

### 2.2 Validation Engine

| ID | Requirement | Priority |
|----|-------------|----------|
| F-VE-01 | Execute Python-based validation rules against uploaded data | Must |
| F-VE-02 | Rules are modular and can be enabled/disabled per validation run | Must |
| F-VE-03 | Support rule categories (Address, Coordinates, EGID, Custom) | Must |
| F-VE-04 | Rules can have severity levels: Error, Warning, Info | Must |
| F-VE-05 | Rules can reference external data sources (APIs, lookup tables) | Should |
| F-VE-06 | Parallel rule execution for performance | Could |
| F-VE-07 | Progress indicator during validation | Should |

### 2.3 Validation Rules - Initial Set

#### 2.3.1 Address Validation
| ID | Rule | Description |
|----|------|-------------|
| R-ADDR-01 | Required fields | Street, PLZ, Ort must be present |
| R-ADDR-02 | PLZ format | Swiss postal codes: 4 digits, valid range |
| R-ADDR-03 | PLZ-Ort consistency | PLZ matches the specified Ort |
| R-ADDR-04 | Canton validation | Canton abbreviation is valid (ZH, BE, etc.) |
| R-ADDR-05 | Street format | No obvious formatting errors |

#### 2.3.2 Coordinate Validation
| ID | Rule | Description |
|----|------|-------------|
| R-COORD-01 | Coordinate presence | Coordinates provided when required |
| R-COORD-02 | Swiss bounds check | Coordinates fall within Switzerland |
| R-COORD-03 | Coordinate system | Detect and validate LV95 vs WGS84 |
| R-COORD-04 | Precision check | Sufficient decimal precision |
| R-COORD-05 | Address-coordinate plausibility | Coordinates roughly match the address |

#### 2.3.3 EGID Validation
| ID | Rule | Description |
|----|------|-------------|
| R-EGID-01 | Format validation | EGID is valid format (numeric, correct length) |
| R-EGID-02 | Uniqueness | No duplicate EGIDs in dataset |
| R-EGID-03 | GWR lookup | EGID exists in federal building register (optional, API) |
| R-EGID-04 | EGID-address consistency | EGID matches the provided address |

#### 2.3.4 General Data Quality
| ID | Rule | Description |
|----|------|-------------|
| R-GEN-01 | Duplicate records | Detect duplicate rows |
| R-GEN-02 | Empty rows | Flag completely empty rows |
| R-GEN-03 | Data types | Values match expected types |
| R-GEN-04 | Encoding issues | Detect character encoding problems |

### 2.4 Results Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| F-DB-01 | Summary statistics (total rows, errors, warnings, passed) | Must |
| F-DB-02 | Visual breakdown by rule category | Must |
| F-DB-03 | Error distribution chart/visualization | Should |
| F-DB-04 | Drill-down to individual errors | Must |
| F-DB-05 | Filter results by severity, rule, or category | Should |
| F-DB-06 | Sort and search within results | Should |
| F-DB-07 | Map visualization for coordinate errors | Could |

### 2.5 Dimensional Analysis (Portfolio Views)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-DIM-01 | Group and filter results by **Region** (Kanton, Gemeinde) | Must |
| F-DIM-02 | Group and filter results by **Sub-Portfolio** (e.g., Verwaltungsgebäude, Wohnliegenschaften) | Must |
| F-DIM-03 | Group and filter results by **Responsible Person** (Verantwortliche/r) | Should |
| F-DIM-04 | Dashboard overview cards showing error counts per dimension | Must |
| F-DIM-05 | Drill-down from dimension summary to detailed records | Must |
| F-DIM-06 | Comparative view: side-by-side quality metrics across dimensions | Should |
| F-DIM-07 | Export filtered results per dimension | Should |

### 2.6 Checker Gallery / Workflow Catalog

| ID | Requirement | Priority |
|----|-------------|----------|
| F-GAL-01 | Card-based gallery view of available validation workflows | Must |
| F-GAL-02 | Each card shows: name, short description, category tag | Must |
| F-GAL-03 | Cards indicate if checker requires specific columns/data | Should |
| F-GAL-04 | Click card to see full documentation before running | Must |
| F-GAL-05 | Category filtering in gallery (Address, Coordinates, EGID, etc.) | Should |
| F-GAL-06 | Search/filter checkers by keyword | Could |
| F-GAL-07 | Favorite/pin frequently used checkers | Could |

### 2.7 Error Report Download

| ID | Requirement | Priority |
|----|-------------|----------|
| F-DL-01 | Download detailed error report as Excel | Must |
| F-DL-02 | Report includes: row number, field, rule, severity, message | Must |
| F-DL-03 | Download annotated original file (errors marked) | Should |
| F-DL-04 | Download summary report as PDF | Could |
| F-DL-05 | Download validation certificate if no errors | Could |

### 2.8 Rule Documentation

| ID | Requirement | Priority |
|----|-------------|----------|
| F-RD-01 | Web page listing all available rules | Must |
| F-RD-02 | Each rule shows: ID, name, description, severity, category | Must |
| F-RD-03 | Example of valid/invalid data for each rule | Should |
| F-RD-04 | Rules documentation auto-generated from Python code | Should |
| F-RD-05 | Downloadable rules documentation (PDF/Markdown) | Could |

---

## 3. Non-Functional Requirements

### 3.1 Data Privacy & Compliance

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-DP-01 | **No persistent storage of uploaded data** | Must |
| NF-DP-02 | Files processed in-memory only | Must |
| NF-DP-03 | All data cleared after session ends or download completes | Must |
| NF-DP-04 | No logging of file contents or PII | Must |
| NF-DP-05 | Session timeout with automatic data purge | Must |
| NF-DP-06 | HTTPS encryption for all data transfer | Must |

### 3.2 Performance

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-PF-01 | Process 10,000 rows within 30 seconds | Should |
| NF-PF-02 | Responsive UI during processing (progress feedback) | Must |
| NF-PF-03 | Concurrent users: minimum 10 simultaneous | Should |

### 3.3 Security

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-SC-01 | Internal network access only (or VPN) | Must |
| NF-SC-02 | Optional: Integration with BBL authentication (LDAP/AD) | Could |
| NF-SC-03 | Input sanitization to prevent code injection | Must |
| NF-SC-04 | Rate limiting to prevent abuse | Should |

### 3.4 Usability

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-UX-01 | German language interface (primary) | Must |
| NF-UX-02 | French and Italian language support | Should |
| NF-UX-03 | Accessible design (WCAG 2.1 AA) | Should |
| NF-UX-04 | Works on modern browsers (Chrome, Firefox, Edge) | Must |
| NF-UX-05 | Mobile-responsive design | Could |

### 3.5 Maintainability

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-MN-01 | Adding new validation rules requires only Python code | Must |
| NF-MN-02 | Rules self-document (metadata in code) | Should |
| NF-MN-03 | Clear separation of frontend/backend/rules | Must |
| NF-MN-04 | Comprehensive test coverage for rules | Should |
| NF-MN-05 | Docker deployment option | Should |

---

## 4. User Stories

### US-01: Basic Validation
> As a BBL data manager, I want to upload an Excel file with building data so that I can identify data quality issues before importing to our systems.

### US-02: Understanding Errors
> As a user, I want to see a clear dashboard summarizing validation results so that I can quickly assess data quality.

### US-03: Fixing Errors
> As a user, I want to download a detailed error report so that I can correct issues in my source data.

### US-04: Learning Rules
> As a new user, I want to view documentation of all validation rules so that I understand what is being checked.

### US-05: Selective Validation
> As a power user, I want to enable/disable specific rules so that I can focus on relevant checks for my use case.

### US-06: Data Privacy
> As a compliance officer, I want assurance that no uploaded data is stored so that we meet data protection requirements.

### US-07: Regional Analysis
> As a portfolio manager, I want to see data quality grouped by Kanton/Region so that I can identify which regions need attention.

### US-08: Portfolio Analysis
> As a team lead, I want to see validation results by sub-portfolio (Verwaltungsgebäude, Wohnliegenschaften, etc.) so that I can prioritize corrections by asset type.

### US-09: Responsibility Assignment
> As a coordinator, I want to filter errors by responsible person so that I can send targeted correction lists to each colleague.

### US-10: Checker Selection
> As a user, I want to browse available checkers in a gallery view and understand what each one does before uploading my file.

---

## 5. Out of Scope (Version 1.0)

- User accounts and saved validation history
- Batch processing of multiple files
- API access for automated validation
- Direct database connections
- Automatic data correction/transformation
- Integration with GIS systems
- Real-time collaboration features

---

## 6. Assumptions & Constraints

### Assumptions
- Users have basic Excel knowledge
- Input files follow a reasonably consistent structure
- Network connectivity to internal servers is reliable
- External API access (e.g., GWR) is available from server

### Constraints
- Must run on BBL internal infrastructure
- No cloud hosting of data
- Budget for external API calls may be limited
- Must comply with Swiss federal data protection guidelines

---

## 7. Success Criteria

1. Users can validate a typical Excel file (5,000 rows) in under 60 seconds
2. Error reports clearly identify issues with row-level precision
3. New validation rules can be added by a Python developer in under 1 hour
4. Zero data persisted after session completion (verified by audit)
5. Positive user feedback from pilot group (>80% satisfaction)

---

## 8. References

- [CheckGWR Service](https://www.cadastre-manual.admin.ch/de/checkservice-checkgwr) - Reference for AV/GWR validation
- [Geopol by INSER](https://www.inser.ch/de/produit/geopol) - Reference for geodata validation platform
- Swiss Federal Building Register (GWR) API documentation
- Swiss Coordinate Systems: LV95, WGS84
