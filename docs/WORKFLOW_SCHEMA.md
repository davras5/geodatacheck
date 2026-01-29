# Workflow JSON Schema

This document defines the `workflow.json` schema used to describe workflows.

---

## Complete Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["id", "type", "name_de", "description_de"],

  "properties": {

    "id": {
      "type": "string",
      "description": "Unique workflow identifier (kebab-case)",
      "example": "address-validation"
    },

    "type": {
      "type": "string",
      "enum": ["checker", "converter", "enricher", "analyzer"],
      "description": "Type of workflow"
    },

    "name": {
      "type": "string",
      "description": "English name"
    },

    "name_de": {
      "type": "string",
      "description": "German name (primary)"
    },

    "name_fr": {
      "type": "string",
      "description": "French name (optional)"
    },

    "description": {
      "type": "string",
      "description": "Short English description"
    },

    "description_de": {
      "type": "string",
      "description": "Short German description (shown on card)"
    },

    "description_long_de": {
      "type": "string",
      "description": "Detailed German description (shown on detail page)"
    },

    "category": {
      "type": "string",
      "enum": ["QUALITÄTSSICHERUNG", "KOORDINATEN", "EGID", "CAD", "BIM", "KONVERTIERUNG"],
      "description": "Category for filtering in UI"
    },

    "icon": {
      "type": "string",
      "description": "Emoji icon for UI",
      "example": "📍"
    },

    "version": {
      "type": "string",
      "description": "Workflow version (semver)",
      "example": "1.0.0"
    },

    "author": {
      "type": "string",
      "description": "Author or responsible team",
      "example": "BBL CAFM"
    },

    "input": {
      "type": "object",
      "description": "Input specification",
      "properties": {
        "formats": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Accepted file extensions",
          "example": [".xlsx", ".xls", ".csv"]
        },
        "max_size_mb": {
          "type": "integer",
          "description": "Maximum file size in MB",
          "default": 50
        },
        "multiple_files": {
          "type": "boolean",
          "description": "Allow multiple file upload",
          "default": false
        }
      }
    },

    "output": {
      "type": "object",
      "description": "Output specification",
      "properties": {
        "formats": {
          "type": "array",
          "items": {"type": "string"},
          "enum": ["dashboard", "excel_report", "pdf_report", "excel_file", "csv_file", "json"],
          "description": "Available output formats"
        },
        "preview": {
          "type": "boolean",
          "description": "Show preview before download",
          "default": true
        }
      }
    },

    "columns": {
      "type": "object",
      "description": "Column requirements (for data workflows)",
      "properties": {
        "required": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Required logical column names"
        },
        "optional": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional logical column names"
        }
      }
    },

    "parameters": {
      "type": "array",
      "description": "User-configurable parameters",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name_de": {"type": "string"},
          "type": {"enum": ["text", "number", "boolean", "select"]},
          "default": {},
          "options": {"type": "array"},
          "required": {"type": "boolean"}
        }
      }
    },

    "rules": {
      "type": "array",
      "description": "Validation rules (for checker workflows)",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Rule ID like R-ADDR-001"},
          "class": {"type": "string", "description": "Python class name"},
          "name_de": {"type": "string"},
          "description_de": {"type": "string"},
          "severity": {"enum": ["error", "warning", "info"]},
          "default_enabled": {"type": "boolean"},
          "category": {"type": "string"}
        }
      }
    },

    "rule_categories": {
      "type": "array",
      "description": "Rule category definitions for UI grouping",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name_de": {"type": "string"},
          "icon": {"type": "string"}
        }
      }
    },

    "requirements_doc": {
      "type": "string",
      "description": "Filename of requirements document (if any)",
      "example": "ANFORDERUNGEN.md"
    }
  }
}
```

---

## Workflow Types

| Type | Description | Has Rules | Output |
|------|-------------|-----------|--------|
| `checker` | Validates data, returns errors | Yes | Dashboard + Report |
| `converter` | Transforms data format | No | Converted file |
| `enricher` | Adds data from external sources | No | Enriched file |
| `analyzer` | Analyzes and reports statistics | No | Statistics report |

---

## Examples

### Checker Workflow

```json
{
  "id": "address-validation",
  "type": "checker",
  "name_de": "Adress-Validierung",
  "description_de": "Validiert Schweizer Adressdaten",
  "category": "QUALITÄTSSICHERUNG",
  "icon": "📍",

  "input": {
    "formats": [".xlsx", ".xls"],
    "max_size_mb": 50
  },

  "output": {
    "formats": ["dashboard", "excel_report"]
  },

  "columns": {
    "required": ["plz", "ort"],
    "optional": ["strasse", "kanton", "egid", "e_coord", "n_coord"]
  },

  "rules": [
    {
      "id": "R-ADDR-001",
      "class": "RequiredFieldsRule",
      "name_de": "Pflichtfelder",
      "description_de": "PLZ und Ort müssen ausgefüllt sein",
      "severity": "error",
      "default_enabled": true,
      "category": "Vollständigkeit"
    }
  ],

  "rule_categories": [
    {"id": "Vollständigkeit", "name_de": "Vollständigkeit", "icon": "📋"}
  ]
}
```

### Converter Workflow

```json
{
  "id": "ifc-to-excel",
  "type": "converter",
  "name_de": "IFC zu Excel",
  "description_de": "Exportiert IFC-Gebäudedaten nach Excel",
  "category": "KONVERTIERUNG",
  "icon": "🔄",

  "input": {
    "formats": [".ifc"],
    "max_size_mb": 200
  },

  "output": {
    "formats": ["excel_file"],
    "preview": true
  },

  "parameters": [
    {
      "id": "include_geometry",
      "name_de": "Geometrie exportieren",
      "type": "boolean",
      "default": false
    },
    {
      "id": "element_types",
      "name_de": "Elementtypen",
      "type": "select",
      "options": ["Alle", "Nur Räume", "Nur Bauteile"],
      "default": "Alle"
    }
  ]
}
```

### Analyzer Workflow

```json
{
  "id": "portfolio-statistics",
  "type": "analyzer",
  "name_de": "Portfolio-Statistiken",
  "description_de": "Analysiert Portfolio und erstellt Statistikbericht",
  "category": "QUALITÄTSSICHERUNG",
  "icon": "📊",

  "input": {
    "formats": [".xlsx", ".xls"]
  },

  "output": {
    "formats": ["dashboard", "pdf_report"]
  }
}
```

---

## Frontend Usage

The frontend reads `workflow.json` to:

1. **Gallery**: Show cards with `name_de`, `description_de`, `icon`, `category`
2. **Detail page**: Show `description_long_de`, `rules` with checkboxes
3. **Upload**: Validate file against `input.formats`, `input.max_size_mb`
4. **Column mapping**: Use `columns.required` / `columns.optional`
5. **Parameters**: Render form fields from `parameters`
6. **Results**: Choose output based on `output.formats`
