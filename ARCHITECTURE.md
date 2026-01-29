# GeoDataCheck - Architecture

**Version**: 1.0 (Prototype)

---

## Folder Structure

```
geodatacheck/
│
├── workflows/                         # All workflows
│   │
│   ├── address-validation/            # One folder per workflow
│   │   ├── workflow.json              # Metadata + rule definitions
│   │   ├── README.md                  # Business documentation
│   │   └── rules.py                   # ALL rules in one file
│   │
│   ├── cafm-basisplan/
│   │   ├── workflow.json
│   │   ├── README.md
│   │   ├── ANFORDERUNGEN.md           # BBL requirements doc
│   │   └── rules.py
│   │
│   ├── ifc-to-excel/
│   │   ├── workflow.json
│   │   ├── README.md
│   │   └── processor.py               # Converter (not rules)
│   │
│   └── egid-validation/
│       ├── workflow.json
│       ├── README.md
│       └── rules.py
│
├── backend/
│   ├── main.py                        # FastAPI app
│   ├── requirements.txt
│   └── core/
│       ├── base.py                    # BaseRule class
│       ├── engine.py                  # Runs validation
│       └── loader.py                  # Auto-discovers workflows
│
├── index.html                         # Frontend (GitHub Pages)
│
└── docs/
    ├── REQUIREMENTS.md
    ├── DESIGNGUIDE.md
    └── ARCHITECTURE.md
```

---

## Key Files

### `workflow.json` - Workflow Metadata

```json
{
  "id": "address-validation",
  "type": "checker",
  "name_de": "Adress-Validierung",
  "description_de": "Validiert Adressdaten für Immobilienportfolios",
  "category": "QUALITÄTSSICHERUNG",
  "icon": "📍",
  "input_formats": [".xlsx", ".xls"],
  "rules_file": "rules.py",

  "rules": [
    {
      "id": "R-ADDR-001",
      "class": "RequiredFieldsRule",
      "name_de": "Pflichtfelder",
      "description_de": "PLZ, Ort und Strasse müssen ausgefüllt sein",
      "severity": "error",
      "default_enabled": true,
      "category": "Vollständigkeit"
    },
    {
      "id": "R-ADDR-002",
      "class": "PLZFormatRule",
      "name_de": "PLZ-Format",
      "description_de": "PLZ muss 4-stellig sein (1000-9999)",
      "severity": "error",
      "default_enabled": true,
      "category": "Format"
    }
  ]
}
```

### `rules.py` - All Rules in One File

```python
"""
Address Validation Rules
========================
All checking rules for address validation in one file.
"""

from core.base import BaseRule, ValidationError, Severity
import pandas as pd


class RequiredFieldsRule(BaseRule):
    """R-ADDR-001: Check required fields are present."""

    rule_id = "R-ADDR-001"

    def validate(self, df, config):
        errors = []
        # ... validation logic
        return errors


class PLZFormatRule(BaseRule):
    """R-ADDR-002: Swiss PLZ must be 4 digits."""

    rule_id = "R-ADDR-002"

    def validate(self, df, config):
        errors = []
        # ... validation logic
        return errors


# Export all rules
ALL_RULES = [
    RequiredFieldsRule,
    PLZFormatRule,
    # ... more rules
]
```

---

## Workflow Types

| Type | Output | Example |
|------|--------|---------|
| `checker` | Error report | Address Validation |
| `converter` | Transformed file | IFC to Excel |

---

## How It Works

1. **Loader** scans `/workflows/*/workflow.json`
2. **UI** shows workflow gallery with checkboxes for rules
3. **User** uploads file + selects rules
4. **Engine** imports `rules.py`, instantiates selected rule classes
5. **Engine** runs each rule, collects errors
6. **UI** shows dashboard + download report
