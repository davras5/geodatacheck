# GeoDataCheck - Design Guide

**Project**: Geo Data Validation Tool for BBL
**Version**: 1.0 Draft
**Date**: January 2026

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (User)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Upload    │  │  Dashboard  │  │   Rules Documentation   │ │
│  │   Interface │  │   View      │  │   Page                  │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                     │               │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Web Application (Backend)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FastAPI / Flask                        │   │
│  ├──────────────┬──────────────┬──────────────┬─────────────┤   │
│  │ Upload       │ Validation   │ Report       │ Rules       │   │
│  │ Handler      │ Engine       │ Generator    │ Registry    │   │
│  └──────────────┴──────┬───────┴──────────────┴─────────────┘   │
│                        │                                         │
│  ┌─────────────────────▼────────────────────────────────────┐   │
│  │              Validation Rules (Python)                    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │   │
│  │  │ Address │ │ Coords  │ │  EGID   │ │ Custom Rules... │ │   │
│  │  │ Rules   │ │ Rules   │ │ Rules   │ │                 │ │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼ (optional, for enhanced validation)
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ GWR API     │  │ PLZ/Ort DB  │  │ Geocoding Service       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow (No Persistence)

```
┌────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│ Upload │───▶│ In-Memory  │───▶│ Validation │───▶│ Results    │
│        │    │ DataFrame  │    │ Engine     │    │ JSON       │
└────────┘    └────────────┘    └────────────┘    └─────┬──────┘
                                                        │
                    ┌───────────────────────────────────┘
                    │
                    ▼
┌────────────┐    ┌────────────┐    ┌────────────┐
│ Dashboard  │◀───│ Session    │───▶│ Download   │
│ Display    │    │ (temp)     │    │ Report     │
└────────────┘    └────────────┘    └────────────┘
                        │
                        ▼
                  ┌────────────┐
                  │ PURGE      │  ← On timeout or completion
                  │ All Data   │
                  └────────────┘
```

---

## 2. Technology Stack

### 2.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React + TypeScript | Modern, maintainable, good ecosystem |
| **UI Framework** | Tailwind CSS + shadcn/ui | Clean, professional, accessible |
| **Charts** | Recharts or Chart.js | Simple, effective visualizations |
| **Backend** | FastAPI (Python) | Fast, modern, native Python for rules |
| **Data Processing** | pandas | Excel handling, data manipulation |
| **Validation Rules** | Pure Python | Easy to write and maintain |
| **Session Management** | In-memory (Redis optional) | No persistence, fast access |
| **Deployment** | Docker + Docker Compose | Portable, reproducible |

### 2.2 Alternative: Simpler Stack

For faster initial development:

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Full-Stack** | Streamlit | Rapid prototyping, Python-native |
| **Or** | Flask + Jinja2 + HTMX | Simple, server-rendered, minimal JS |

---

## 3. Python Validation Rules Framework

### 3.1 Rule Definition Pattern

Each rule is a Python class that inherits from a base validator:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any
import pandas as pd

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class Category(Enum):
    ADDRESS = "address"
    COORDINATES = "coordinates"
    EGID = "egid"
    GENERAL = "general"

@dataclass
class ValidationError:
    """Represents a single validation error."""
    row_index: int
    column: str
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    value: Any = None
    suggestion: Optional[str] = None

@dataclass
class RuleMetadata:
    """Metadata for documentation generation."""
    id: str
    name: str
    description: str
    category: Category
    severity: Severity
    example_valid: Optional[str] = None
    example_invalid: Optional[str] = None

class BaseRule(ABC):
    """Base class for all validation rules."""

    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Return rule metadata for documentation."""
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
        """
        Validate the dataframe and return list of errors.

        Args:
            df: The pandas DataFrame to validate
            config: Configuration dict with column mappings, options

        Returns:
            List of ValidationError objects
        """
        pass

    def is_applicable(self, df: pd.DataFrame, config: dict) -> bool:
        """Check if this rule should run (e.g., required columns exist)."""
        return True
```

### 3.2 Example Rule Implementations

```python
class PLZFormatRule(BaseRule):
    """Validates Swiss postal code format."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-ADDR-02",
            name="PLZ Format",
            description="Swiss postal codes must be 4 digits between 1000 and 9999",
            category=Category.ADDRESS,
            severity=Severity.ERROR,
            example_valid="8001",
            example_invalid="123, 00100, 8001a"
        )

    def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
        errors = []
        plz_col = config.get('columns', {}).get('plz', 'PLZ')

        if plz_col not in df.columns:
            return errors

        for idx, row in df.iterrows():
            value = row[plz_col]

            if pd.isna(value):
                continue  # Handled by required fields rule

            # Convert to string and check format
            plz_str = str(value).strip()

            if not plz_str.isdigit() or len(plz_str) != 4:
                errors.append(ValidationError(
                    row_index=idx,
                    column=plz_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name,
                    severity=self.metadata.severity,
                    message=f"Invalid PLZ format: '{value}'. Must be 4 digits.",
                    value=value
                ))
            elif not (1000 <= int(plz_str) <= 9999):
                errors.append(ValidationError(
                    row_index=idx,
                    column=plz_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name,
                    severity=self.metadata.severity,
                    message=f"PLZ out of range: '{value}'. Must be 1000-9999.",
                    value=value
                ))

        return errors


class SwissBoundsRule(BaseRule):
    """Validates coordinates are within Switzerland."""

    # Switzerland approximate bounds (LV95)
    CH_BOUNDS_LV95 = {
        'e_min': 2485000, 'e_max': 2834000,  # Easting
        'n_min': 1075000, 'n_max': 1296000   # Northing
    }

    # Switzerland approximate bounds (WGS84)
    CH_BOUNDS_WGS84 = {
        'lat_min': 45.8, 'lat_max': 47.9,
        'lon_min': 5.9, 'lon_max': 10.5
    }

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-COORD-02",
            name="Swiss Bounds Check",
            description="Coordinates must fall within Switzerland's boundaries",
            category=Category.COORDINATES,
            severity=Severity.ERROR,
            example_valid="E: 2600000, N: 1200000 (LV95)",
            example_invalid="E: 1000000, N: 500000"
        )

    def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
        errors = []
        coord_system = config.get('coordinate_system', 'LV95')

        e_col = config.get('columns', {}).get('easting', 'E')
        n_col = config.get('columns', {}).get('northing', 'N')

        if e_col not in df.columns or n_col not in df.columns:
            return errors

        bounds = self.CH_BOUNDS_LV95 if coord_system == 'LV95' else self.CH_BOUNDS_WGS84

        for idx, row in df.iterrows():
            e_val = row[e_col]
            n_val = row[n_col]

            if pd.isna(e_val) or pd.isna(n_val):
                continue

            try:
                e = float(e_val)
                n = float(n_val)

                if coord_system == 'LV95':
                    if not (bounds['e_min'] <= e <= bounds['e_max']):
                        errors.append(self._create_error(idx, e_col, e, "Easting"))
                    if not (bounds['n_min'] <= n <= bounds['n_max']):
                        errors.append(self._create_error(idx, n_col, n, "Northing"))
                else:  # WGS84
                    if not (bounds['lon_min'] <= e <= bounds['lon_max']):
                        errors.append(self._create_error(idx, e_col, e, "Longitude"))
                    if not (bounds['lat_min'] <= n <= bounds['lat_max']):
                        errors.append(self._create_error(idx, n_col, n, "Latitude"))

            except (ValueError, TypeError):
                errors.append(ValidationError(
                    row_index=idx,
                    column=f"{e_col}/{n_col}",
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name,
                    severity=Severity.ERROR,
                    message=f"Invalid coordinate values: E={e_val}, N={n_val}",
                    value=f"E={e_val}, N={n_val}"
                ))

        return errors

    def _create_error(self, idx, col, value, coord_type):
        return ValidationError(
            row_index=idx,
            column=col,
            rule_id=self.metadata.id,
            rule_name=self.metadata.name,
            severity=self.metadata.severity,
            message=f"{coord_type} outside Switzerland: {value}",
            value=value
        )


class EGIDFormatRule(BaseRule):
    """Validates EGID format."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-EGID-01",
            name="EGID Format",
            description="EGID must be a positive integer (federal building identifier)",
            category=Category.EGID,
            severity=Severity.ERROR,
            example_valid="123456789",
            example_invalid="12-345, EGID123, -500"
        )

    def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
        errors = []
        egid_col = config.get('columns', {}).get('egid', 'EGID')

        if egid_col not in df.columns:
            return errors

        for idx, row in df.iterrows():
            value = row[egid_col]

            if pd.isna(value):
                continue

            try:
                egid = int(float(value))  # Handle "123.0" from Excel
                if egid <= 0:
                    raise ValueError("EGID must be positive")
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    row_index=idx,
                    column=egid_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name,
                    severity=self.metadata.severity,
                    message=f"Invalid EGID format: '{value}'. Must be a positive integer.",
                    value=value
                ))

        return errors
```

### 3.3 Rule Registry

```python
class RuleRegistry:
    """Central registry for all validation rules."""

    def __init__(self):
        self._rules: dict[str, BaseRule] = {}

    def register(self, rule: BaseRule) -> None:
        """Register a rule instance."""
        self._rules[rule.metadata.id] = rule

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Get a specific rule by ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def get_rules_by_category(self, category: Category) -> List[BaseRule]:
        """Get all rules in a category."""
        return [r for r in self._rules.values()
                if r.metadata.category == category]

    def get_documentation(self) -> List[dict]:
        """Generate documentation for all rules."""
        return [
            {
                'id': r.metadata.id,
                'name': r.metadata.name,
                'description': r.metadata.description,
                'category': r.metadata.category.value,
                'severity': r.metadata.severity.value,
                'example_valid': r.metadata.example_valid,
                'example_invalid': r.metadata.example_invalid,
            }
            for r in sorted(self._rules.values(), key=lambda x: x.metadata.id)
        ]

# Auto-discover and register rules
def create_default_registry() -> RuleRegistry:
    """Create registry with all default rules."""
    registry = RuleRegistry()

    # Register all rules
    registry.register(PLZFormatRule())
    registry.register(SwissBoundsRule())
    registry.register(EGIDFormatRule())
    # ... register more rules

    return registry
```

### 3.4 Adding a New Rule

To add a new validation rule, developers simply:

1. Create a new Python file in `rules/` directory (or add to existing category file)
2. Define a class inheriting from `BaseRule`
3. Implement `metadata` property and `validate` method
4. Register the rule in the registry

```python
# rules/custom/my_new_rule.py

class MyCustomRule(BaseRule):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-CUSTOM-01",
            name="My Custom Check",
            description="Description of what this rule checks",
            category=Category.GENERAL,
            severity=Severity.WARNING,
        )

    def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
        errors = []
        # Your validation logic here
        return errors
```

---

## 4. User Interface Design

### 4.1 Design Principles

| Principle | Application |
|-----------|-------------|
| **Clarity** | Clear feedback at every step, no ambiguous states |
| **Efficiency** | Minimal clicks to complete validation |
| **Trust** | Visible privacy indicators, clear data handling |
| **Professional** | Swiss federal government aesthetic, accessible |

### 4.2 Color Palette

```
Primary:       #1E3A5F (Federal blue)
Secondary:     #E3000F (Swiss red - for errors/alerts)
Success:       #2E7D32 (Green)
Warning:       #F57C00 (Orange)
Info:          #1976D2 (Blue)
Background:    #F5F5F5 (Light gray)
Surface:       #FFFFFF (White)
Text Primary:  #212121
Text Secondary:#757575
```

### 4.3 Page Layouts

#### 4.3.1 Home / Checker Gallery (Geopol-inspired)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
│  BBL · Bundesamt für Bauten und Logistik                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  🔍 Search checkers...           Filter: [All Categories ▼]            │
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌──────────┐│
│  │ QUALITÄTSSICHERUNG      │  │ QUALITÄTSSICHERUNG      │  │ EGID     ││
│  │                         │  │                         │  │          ││
│  │ Portfolio               │  │ Adress-Checker          │  │ EGID/GWR ││
│  │ Vollständigkeits-Check  │  │                         │  │ Checker  ││
│  │                         │  │ Prüft Schweizer         │  │          ││
│  │ Prüft die Vollständig-  │  │ Adressen auf Format,    │  │ Validiert││
│  │ keit aller Pflicht-     │  │ PLZ-Ort Konsistenz      │  │ EGID-Num-││
│  │ felder im Portfolio.    │  │ und Kantone.            │  │ mern...  ││
│  │                         │  │                         │  │          ││
│  │ ☐ Erfordert: PLZ, Ort,  │  │ ☐ Erfordert: Strasse,   │  │ ☐ Erford-││
│  │   Strasse, EGID         │  │   PLZ, Ort, Kanton      │  │   ert:   ││
│  │                         │  │                         │  │   EGID   ││
│  │ [Checker starten    →]  │  │ [Checker starten    →]  │  │ [Start →]││
│  └─────────────────────────┘  └─────────────────────────┘  └──────────┘│
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌──────────┐│
│  │ KOORDINATEN             │  │ QUALITÄTSSICHERUNG      │  │ CUSTOM   ││
│  │                         │  │                         │  │          ││
│  │ Koordinaten-Checker     │  │ Duplikat-Erkennung      │  │ Portfolio││
│  │ (LV95/WGS84)            │  │                         │  │ Spezial  ││
│  │                         │  │ Erkennt doppelte        │  │          ││
│  │ Prüft ob Koordinaten    │  │ Einträge basierend      │  │ BBL-spe- ││
│  │ innerhalb der Schweiz   │  │ auf konfigurierbaren    │  │ zifische ││
│  │ liegen und korrekt...   │  │ Schlüsselfeldern.       │  │ Checks...││
│  │                         │  │                         │  │          ││
│  │ [Checker starten    →]  │  │ [Checker starten    →]  │  │ [Start →]││
│  └─────────────────────────┘  └─────────────────────────┘  └──────────┘│
│                                                                         │
│  🔒 Ihre Daten werden lokal verarbeitet und niemals gespeichert.       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.2 Checker Detail & Upload Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
├─────────────────────────────────────────────────────────────────────────┤
│  ← Zurück zur Übersicht                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │  QUALITÄTSSICHERUNG                                      ☆     │   │
│  │                                                                 │   │
│  │  Adress-Checker                                                 │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  Prüft Schweizer Adressen auf Korrektheit und Konsistenz.      │   │
│  │  Dieser Checker validiert PLZ-Format (4-stellig), PLZ-Ort      │   │
│  │  Zuordnung, Kantonsabkürzungen und Strassenformate.            │   │
│  │                                                                 │   │
│  │  ┌─ Enthaltene Prüfungen ─────────────────────────────────┐    │   │
│  │  │  • R-ADDR-01: Pflichtfelder vorhanden                  │    │   │
│  │  │  • R-ADDR-02: PLZ-Format (4 Ziffern, 1000-9999)        │    │   │
│  │  │  • R-ADDR-03: PLZ-Ort Konsistenz                       │    │   │
│  │  │  • R-ADDR-04: Gültige Kantonsabkürzung                 │    │   │
│  │  │  • R-ADDR-05: Strassenformat                           │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  │                                                                 │   │
│  │  ● Informationen                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Source file (Excel .xlsx, .xls)                         │  │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  📁 Datei auswählen    Keine Datei ausgewählt      │  │  │   │
│  │  │  └────────────────────────────────────────────────────┘  │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  │                                                                 │   │
│  │  ● Parameter                                                    │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Spalte für PLZ:        [Auto-detect          ▼]         │  │   │
│  │  │  Spalte für Ort:        [Auto-detect          ▼]         │  │   │
│  │  │  Spalte für Strasse:    [Auto-detect          ▼]         │  │   │
│  │  │  Spalte für Kanton:     [Auto-detect          ▼]         │  │   │
│  │  │                                                          │  │   │
│  │  │  Gruppierung für Dashboard:                              │  │   │
│  │  │  Spalte für Region:     [Kanton               ▼]         │  │   │
│  │  │  Spalte für Portfolio:  [Portfolio_Typ        ▼]         │  │   │
│  │  │  Spalte für Zuständig:  [Verantwortlich       ▼]         │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  │                                                                 │   │
│  │          [ Ausführen ]                                          │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  🔒 Ihre Daten werden lokal verarbeitet und niemals gespeichert.       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.3 Results Dashboard with Dimensional Analysis

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
├─────────────────────────────────────────────────────────────────────────┤
│  ← Zurück    📄 portfolio_2024.xlsx    ⏱️ Session: 14:32               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    VALIDIERUNGSERGEBNIS                           │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐              │ │
│  │  │  1,247  │  │    23   │  │    45   │  │  1,179  │              │ │
│  │  │  Total  │  │ Fehler  │  │ Warnun- │  │ Bestanden│             │ │
│  │  │  Zeilen │  │   🔴    │  │ gen 🟡  │  │    🟢   │              │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ ANSICHT ────────────────────────────────────────────────────────┐  │
│  │  [Übersicht]  [Nach Region]  [Nach Portfolio]  [Nach Zuständig]  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ════════════════════════════════════════════════════════════════════  │
│  NACH REGION (Kanton)                                                   │
│  ════════════════════════════════════════════════════════════════════  │
│                                                                         │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────┐ │
│  │ Zürich (ZH)    │ │ Bern (BE)      │ │ Waadt (VD)     │ │ Genf (GE)│ │
│  │ ───────────────│ │ ───────────────│ │ ───────────────│ │ ─────────│ │
│  │ 423 Objekte    │ │ 312 Objekte    │ │ 198 Objekte    │ │ 156 Obj. │ │
│  │                │ │                │ │                │ │          │ │
│  │ 🔴 8 Fehler    │ │ 🔴 3 Fehler    │ │ 🔴 7 Fehler    │ │ 🔴 2     │ │
│  │ 🟡 12 Warnungen│ │ 🟡 5 Warnungen │ │ 🟡 14 Warnungen│ │ 🟡 6     │ │
│  │                │ │                │ │                │ │          │ │
│  │ ▓▓▓▓▓▓▓░░░ 95% │ │ ▓▓▓▓▓▓▓▓▓░ 97% │ │ ▓▓▓▓▓▓░░░░ 89% │ │ ▓▓▓▓▓▓▓▓ │ │
│  │ [Details →]    │ │ [Details →]    │ │ [Details →]    │ │ [    →] │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────┘ │
│                                                                         │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐              │
│  │ Basel (BS/BL)  │ │ Aargau (AG)    │ │ Andere (8)     │              │
│  │ ───────────────│ │ ───────────────│ │ ───────────────│              │
│  │ 89 Objekte     │ │ 45 Objekte     │ │ 24 Objekte     │              │
│  │ 🔴 1  🟡 3     │ │ 🔴 2  🟡 4     │ │ 🔴 0  🟡 1     │              │
│  │ [Details →]    │ │ [Details →]    │ │ [Details →]    │              │
│  └────────────────┘ └────────────────┘ └────────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.4 Dashboard: Portfolio View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
├─────────────────────────────────────────────────────────────────────────┤
│  ← Zurück    📄 portfolio_2024.xlsx    ⏱️ Session: 13:45               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ ANSICHT ────────────────────────────────────────────────────────┐  │
│  │  [Übersicht]  [Nach Region]  [Nach Portfolio]  [Nach Zuständig]  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ════════════════════════════════════════════════════════════════════  │
│  NACH PORTFOLIO-TYP                                                     │
│  ════════════════════════════════════════════════════════════════════  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Portfolio-Typ          │ Objekte │ Fehler │ Warn. │ Quote     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  Verwaltungsgebäude     │    534  │   12   │   18  │ ▓▓▓▓▓▓▓░ 94% │ │
│  │  Wohnliegenschaften     │    298  │    5   │    9  │ ▓▓▓▓▓▓▓▓ 97% │ │
│  │  Technische Bauten      │    156  │    3   │   12  │ ▓▓▓▓▓▓▓░ 96% │ │
│  │  Kulturbauten           │     89  │    2   │    4  │ ▓▓▓▓▓▓▓▓ 97% │ │
│  │  Historische Gebäude    │     78  │    1   │    2  │ ▓▓▓▓▓▓▓▓▓ 99%│ │
│  │  Übrige                 │     92  │    0   │    0  │ ▓▓▓▓▓▓▓▓▓ 100│ │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ PROBLEMÜBERSICHT: Verwaltungsgebäude (534 Objekte) ────────────┐   │
│  │                                                                 │   │
│  │  Top Fehler:                      Top Warnungen:                │   │
│  │  1. PLZ-Format (5)                1. Koordinaten-Präzision (8)  │   │
│  │  2. EGID fehlt (4)                2. Strassen-Format (6)        │   │
│  │  3. Koordinaten ausserhalb (3)    3. Kanton nicht angegeben (4) │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📥 DOWNLOAD                                                     │   │
│  │  [ Alle Fehler (Excel) ]  [ Nur Verwaltungsgebäude (Excel) ]    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.5 Dashboard: Responsible Person View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─ ANSICHT ────────────────────────────────────────────────────────┐  │
│  │  [Übersicht]  [Nach Region]  [Nach Portfolio]  [Nach Zuständig]  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ════════════════════════════════════════════════════════════════════  │
│  NACH ZUSTÄNDIGER PERSON                                                │
│  ════════════════════════════════════════════════════════════════════  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Zuständig               │ Objekte │ Fehler │ Zu bearbeiten     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  Müller, Hans            │    234  │    8   │ [📥 Export]       │   │
│  │  Schmidt, Anna           │    198  │    5   │ [📥 Export]       │   │
│  │  Weber, Peter            │    312  │    4   │ [📥 Export]       │   │
│  │  Brunner, Maria          │    156  │    3   │ [📥 Export]       │   │
│  │  Fischer, Thomas         │    189  │    2   │ [📥 Export]       │   │
│  │  Keller, Sandra          │    158  │    1   │ [📥 Export]       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  💡 "Export" lädt Excel mit Fehlern für diese Person herunter          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.6 Detailed Error List (Drill-Down)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                              [DE] [FR] [IT]   [?]     │
├─────────────────────────────────────────────────────────────────────────┤
│  ← Zurück zum Dashboard    Region: Zürich (ZH) · 423 Objekte           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ FEHLER IN REGION ZÜRICH                      🔍 Suchen...       │   │
│  │ Filter: [Alle Schweregrade ▼] [Alle Regeln ▼]                   │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ Zeile │ Feld   │ Regel        │ Schwere  │ Meldung              │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │   15  │ PLZ    │ PLZ-Format   │ 🔴 Fehler│ Ungültiges Format:   │   │
│  │       │        │              │          │ '801' (muss 4-stell.)│   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │   23  │ E_COORD│ CH-Grenzen   │ 🔴 Fehler│ Koordinate ausser-   │   │
│  │       │        │              │          │ halb CH: 1234567     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │   45  │ EGID   │ EGID-Format  │ 🔴 Fehler│ Ungültig: 'ABC123'   │   │
│  │       │        │              │          │ (muss numerisch sein)│   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │   67  │ Ort    │ PLZ-Ort      │ 🟡 Warn. │ PLZ 8000 passt nicht │   │
│  │       │        │              │          │ zu Ort 'Winterthur'  │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ... weitere 16 Einträge ...                      [1] 2 3 >     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [ 📥 Export dieser Ansicht (Excel) ]                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.7 Rules Documentation Page

```
┌─────────────────────────────────────────────────────────────┐
│  🏛️ GeoDataCheck                    [DE] [FR] [IT]   [?]   │
├─────────────────────────────────────────────────────────────┤
│  ← Back                       📋 Validation Rules           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🏠 ADDRESS VALIDATION                               │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │                                                     │   │
│  │ R-ADDR-01 · Required Fields                  Error  │   │
│  │ ─────────────────────────────────────────────────── │   │
│  │ Street, PLZ, and Ort must be present               │   │
│  │ ✓ Valid: "Bundesplatz 1, 3003, Bern"              │   │
│  │ ✗ Invalid: "Bundesplatz 1, , " (missing PLZ/Ort)  │   │
│  │                                                     │   │
│  │ R-ADDR-02 · PLZ Format                       Error  │   │
│  │ ─────────────────────────────────────────────────── │   │
│  │ Swiss postal codes must be 4 digits (1000-9999)    │   │
│  │ ✓ Valid: "8001"                                    │   │
│  │ ✗ Invalid: "123", "8001a"                          │   │
│  │                                                     │   │
│  │ ...                                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📍 COORDINATE VALIDATION                            │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ R-COORD-01 · Coordinate Presence            Warning │   │
│  │ R-COORD-02 · Swiss Bounds Check              Error  │   │
│  │ R-COORD-03 · Coordinate System Detection    Warning │   │
│  │ ...                                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ 📥 Download Rules as PDF ]                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Expected Data Model

### 5.1 Input Excel Structure

The uploaded Excel files should contain building/property data with the following column types:

#### Core Data Columns (for validation)
| Column | Description | Example | Used by |
|--------|-------------|---------|---------|
| EGID | Federal building identifier | 123456789 | EGID rules |
| Strasse | Street name and number | Bundesplatz 1 | Address rules |
| PLZ | Postal code | 3003 | Address rules |
| Ort | City/town | Bern | Address rules |
| Kanton | Canton abbreviation | BE | Address rules |
| E_COORD / X | Easting (LV95) or Longitude (WGS84) | 2600000 | Coordinate rules |
| N_COORD / Y | Northing (LV95) or Latitude (WGS84) | 1200000 | Coordinate rules |

#### Dimension Columns (for dashboard grouping)
| Column | Description | Example | Dashboard View |
|--------|-------------|---------|----------------|
| Region | Geographic grouping | Zürich, Bern, Romandie | Region view |
| Kanton | Canton (can also be used for region) | ZH, BE, VD | Region view |
| Portfolio_Typ | Asset category | Verwaltungsgebäude | Portfolio view |
| Verantwortlich | Responsible person | Müller, Hans | Responsibility view |
| Abteilung | Department | Immobilien Ost | Responsibility view |

### 5.2 Column Auto-Detection

The system will attempt to auto-detect columns using common naming patterns:

```python
COLUMN_PATTERNS = {
    'plz': ['plz', 'postleitzahl', 'postal_code', 'zip'],
    'ort': ['ort', 'stadt', 'gemeinde', 'city', 'town', 'locality'],
    'strasse': ['strasse', 'street', 'adresse', 'address', 'str'],
    'kanton': ['kanton', 'kt', 'canton', 'state'],
    'egid': ['egid', 'gebäude_id', 'building_id', 'geb_id'],
    'easting': ['e', 'e_coord', 'x', 'x_coord', 'easting', 'lon', 'longitude'],
    'northing': ['n', 'n_coord', 'y', 'y_coord', 'northing', 'lat', 'latitude'],
    'region': ['region', 'gebiet', 'zone'],
    'portfolio': ['portfolio', 'portfolio_typ', 'kategorie', 'type', 'asset_type'],
    'responsible': ['verantwortlich', 'zuständig', 'owner', 'responsible', 'bearbeiter'],
}
```

---

## 6. API Design

### 5.1 Endpoints

```
POST   /api/validate
       - Upload file and run validation
       - Request: multipart/form-data (file + config JSON)
       - Response: { session_id, results }

GET    /api/session/{session_id}/results
       - Get validation results
       - Response: { summary, errors[] }

GET    /api/session/{session_id}/download/report
       - Download error report (Excel)
       - Response: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

GET    /api/session/{session_id}/download/annotated
       - Download annotated original file
       - Response: Excel file

DELETE /api/session/{session_id}
       - Explicitly delete session data
       - Response: { success: true }

GET    /api/rules
       - Get all validation rules documentation
       - Response: { rules[] }

GET    /api/rules/{category}
       - Get rules by category
       - Response: { rules[] }
```

### 5.2 Session Management

```python
# Session data structure (in-memory only)
class ValidationSession:
    session_id: str
    created_at: datetime
    expires_at: datetime

    # Data (never persisted to disk)
    original_data: pd.DataFrame  # Uploaded data
    results: List[ValidationError]  # Validation results
    config: dict  # Column mappings, enabled rules

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def cleanup(self) -> None:
        """Explicitly clear all data."""
        self.original_data = None
        self.results = None

# Background task: purge expired sessions
async def cleanup_expired_sessions():
    while True:
        for session_id, session in sessions.items():
            if session.is_expired():
                session.cleanup()
                del sessions[session_id]
        await asyncio.sleep(60)  # Check every minute
```

---

## 7. Project Structure

```
geodatacheck/
├── README.md
├── REQUIREMENTS.md
├── DESIGNGUIDE.md
├── docker-compose.yml
├── Dockerfile
│
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints
│   │   └── models.py           # Pydantic models
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── session.py          # Session management
│   │   ├── file_handler.py     # Excel parsing
│   │   └── report_generator.py # Excel/PDF reports
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseRule, ValidationError
│   │   ├── engine.py           # Validation orchestration
│   │   ├── registry.py         # Rule registry
│   │   │
│   │   └── rules/
│   │       ├── __init__.py
│   │       ├── address.py      # Address validation rules
│   │       ├── coordinates.py  # Coordinate validation rules
│   │       ├── egid.py         # EGID validation rules
│   │       └── general.py      # General quality rules
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_rules.py
│       └── test_api.py
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Upload.tsx
│   │   │   ├── Results.tsx
│   │   │   └── Rules.tsx
│   │   ├── components/
│   │   │   ├── FileUploader.tsx
│   │   │   ├── ResultsDashboard.tsx
│   │   │   └── RulesTable.tsx
│   │   └── api/
│   │       └── client.ts
│   └── public/
│
└── data/                       # Sample test data (not production data)
    └── sample_buildings.xlsx
```

---

## 8. Deployment Options

### 7.1 Docker Deployment (Recommended)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SESSION_TIMEOUT_MINUTES=15
      - MAX_FILE_SIZE_MB=50
    # No volumes for data persistence (by design)

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

### 7.2 Security Considerations

- Deploy behind BBL internal firewall/VPN
- HTTPS termination at load balancer
- No external network access except whitelisted APIs (GWR)
- Regular security updates for dependencies
- Input validation and file type verification

---

## 9. Future Extensions

| Extension | Description | Complexity |
|-----------|-------------|------------|
| API Mode | Automated validation via REST API | Medium |
| Batch Upload | Multiple files in one session | Medium |
| GWR Integration | Live EGID verification | High |
| Map View | Visualize coordinate errors on map | Medium |
| Custom Rules UI | Non-developers can create simple rules | High |
| Scheduled Jobs | Regular validation of data sources | High |

---

## 10. Open Questions for Discussion

1. **Authentication**: Should the tool require BBL login, or is network restriction sufficient?

2. **File Size**: What's the maximum expected file size? (affects memory planning)

3. **External APIs**: Which external services (GWR, geocoding) are approved for use?

4. **Languages**: Is Italian support needed for v1.0, or can it wait?

5. **Deployment**: Preferred infrastructure? (VM, Kubernetes, existing platform)

6. **Timeline**: Target launch date for pilot/production?
