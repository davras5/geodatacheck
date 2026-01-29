# Adress-Validierung

**Workflow-ID**: `address-validation`
**Typ**: Checker
**Kategorie**: Qualitätssicherung

---

## Beschreibung

Dieser Workflow validiert Adressdaten für Schweizer Immobilienportfolios. Er prüft:

- Vollständigkeit der Pflichtfelder (PLZ, Ort)
- Format von PLZ, Kanton, EGID
- Koordinaten innerhalb der Schweiz (LV95/WGS84)
- Doppelte Adressen und EGIDs

---

## Eingabe

**Dateiformate**: Excel (.xlsx, .xls)

**Erwartete Spalten**:

| Spalte | Pflicht | Beschreibung | Beispiel |
|--------|---------|--------------|----------|
| PLZ | Ja | Postleitzahl | 8001 |
| Ort | Ja | Ortschaft | Zürich |
| Strasse | Nein | Strassenname | Bahnhofstrasse |
| Hausnummer | Nein | Hausnummer | 42a |
| Kanton | Nein | Kantonsabkürzung | ZH |
| EGID | Nein | Gebäudeidentifikator | 123456789 |
| E_COORD | Nein | E-Koordinate (LV95 oder WGS84) | 2683000 |
| N_COORD | Nein | N-Koordinate (LV95 oder WGS84) | 1248000 |

---

## Prüfregeln

### Vollständigkeit

| ID | Regel | Schweregrad |
|----|-------|-------------|
| R-ADDR-001 | Pflichtfelder (PLZ, Ort) | Fehler |
| R-ADDR-005 | Koordinaten vorhanden | Warnung |
| R-ADDR-008 | EGID vorhanden | Fehler |

### Formatprüfung

| ID | Regel | Schweregrad |
|----|-------|-------------|
| R-ADDR-002 | PLZ-Format (4-stellig, 1000-9999) | Fehler |
| R-ADDR-003 | Kanton gültig (ZH, BE, etc.) | Fehler |
| R-ADDR-004 | Strassenformat | Warnung |
| R-ADDR-007 | EGID-Format (positive Ganzzahl) | Fehler |

### Konsistenzprüfung

| ID | Regel | Schweregrad |
|----|-------|-------------|
| R-ADDR-006 | Koordinaten innerhalb Schweiz | Fehler |

### Duplikaterkennung

| ID | Regel | Schweregrad |
|----|-------|-------------|
| R-ADDR-009 | Doppelte Adressen | Warnung |
| R-ADDR-010 | Doppelte EGIDs | Warnung |

---

## Ausgabe

- **Dashboard**: Übersicht mit Fehlerstatistiken
- **Excel-Report**: Detaillierte Fehlerliste mit Zeilennummern

---

## Kontakt

BBL - Bundesamt für Bauten und Logistik
