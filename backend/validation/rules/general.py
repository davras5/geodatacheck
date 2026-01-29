"""
General data quality validation rules.
"""

from typing import List, Dict, Any, Set, Tuple
import pandas as pd
import hashlib

from ..base import BaseRule, RuleMetadata, ValidationError, Category, Severity


class DuplicateRowsRule(BaseRule):
    """Detects duplicate rows in the dataset."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-GEN-01",
            name="Duplicate Rows",
            name_de="Doppelte Zeilen",
            description="Detects rows that appear to be duplicates based on key fields",
            description_de="Erkennt Zeilen, die auf Basis von Schlüsselfeldern Duplikate zu sein scheinen",
            category=Category.GENERAL,
            severity=Severity.WARNING,
            required_columns=[],
            example_valid="Jede Zeile ist einzigartig",
            example_invalid="Zeile 5 und Zeile 10 sind identisch",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        # Use key columns if specified, otherwise use all columns
        key_cols = config.get('options', {}).get('duplicate_key_columns', None)

        if key_cols:
            # Filter to existing columns
            key_cols = [c for c in key_cols if c in df.columns]
            if not key_cols:
                return errors
            check_df = df[key_cols]
        else:
            check_df = df

        # Find duplicates
        seen: Dict[str, int] = {}

        for idx, row in check_df.iterrows():
            # Create a hash of the row values
            row_str = '|'.join(str(v) for v in row.values)
            row_hash = hashlib.md5(row_str.encode()).hexdigest()

            if row_hash in seen:
                first_idx = seen[row_hash]
                errors.append(ValidationError(
                    row_index=idx,
                    column='(alle)',
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"Mögliches Duplikat von Zeile {first_idx + 2}",
                    value=None,
                    suggestion="Prüfen Sie, ob diese Zeile versehentlich doppelt erfasst wurde",
                ))
            else:
                seen[row_hash] = idx

        return errors


class EmptyRowsRule(BaseRule):
    """Detects completely empty rows."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-GEN-02",
            name="Empty Rows",
            name_de="Leere Zeilen",
            description="Detects rows where all cells are empty",
            description_de="Erkennt Zeilen, in denen alle Zellen leer sind",
            category=Category.GENERAL,
            severity=Severity.INFO,
            required_columns=[],
            example_valid="Zeile hat mindestens einen Wert",
            example_invalid="Komplett leere Zeile",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for idx, row in df.iterrows():
            # Check if all values are empty/NaN
            is_empty = all(
                pd.isna(v) or str(v).strip() == ''
                for v in row.values
            )

            if is_empty:
                errors.append(ValidationError(
                    row_index=idx,
                    column='(alle)',
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message="Zeile ist komplett leer",
                    value=None,
                ))

        return errors


class DataTypeConsistencyRule(BaseRule):
    """Checks for inconsistent data types in columns."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-GEN-03",
            name="Data Type Consistency",
            name_de="Datentyp-Konsistenz",
            description="Checks that numeric columns contain only numeric values",
            description_de="Prüft, ob numerische Spalten nur numerische Werte enthalten",
            category=Category.GENERAL,
            severity=Severity.WARNING,
            required_columns=[],
            example_valid="PLZ-Spalte enthält nur Zahlen",
            example_invalid="PLZ-Spalte enthält 'k.A.', 'n/a'",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        # Check numeric columns
        numeric_cols = config.get('options', {}).get('numeric_columns', [])

        # Auto-detect from column mappings
        columns = config.get('columns', {})
        for logical_name in ['plz', 'egid', 'easting', 'northing']:
            if logical_name in columns:
                col = columns[logical_name]
                if col in df.columns and col not in numeric_cols:
                    numeric_cols.append(col)

        for col in numeric_cols:
            if col not in df.columns:
                continue

            for idx, row in df.iterrows():
                value = row[col]

                if pd.isna(value) or str(value).strip() == '':
                    continue

                # Check if value is numeric
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        row_index=idx,
                        column=col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"Nicht-numerischer Wert in numerischer Spalte: '{value}'",
                        value=value,
                    ))

        return errors


class EncodingIssuesRule(BaseRule):
    """Detects character encoding problems."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-GEN-04",
            name="Encoding Issues",
            name_de="Zeichenkodierung",
            description="Detects potential character encoding problems (replacement characters, etc.)",
            description_de="Erkennt mögliche Zeichenkodierungsprobleme (Ersetzungszeichen, etc.)",
            category=Category.GENERAL,
            severity=Severity.WARNING,
            required_columns=[],
            example_valid="Zürich, Genève, Müller",
            example_invalid="Z�rich, Gen�ve, M�ller",
        )

    # Common encoding problem indicators
    ENCODING_ISSUES = [
        '�',      # Replacement character
        'Ã¼',    # UTF-8 interpreted as Latin-1 (ü)
        'Ã¤',    # UTF-8 interpreted as Latin-1 (ä)
        'Ã¶',    # UTF-8 interpreted as Latin-1 (ö)
        'Ã©',    # UTF-8 interpreted as Latin-1 (é)
        'Ã¨',    # UTF-8 interpreted as Latin-1 (è)
        'Ã ',    # UTF-8 interpreted as Latin-1 (à)
        '\x00',  # Null character
    ]

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []

        for col in df.columns:
            for idx, row in df.iterrows():
                value = row[col]

                if pd.isna(value):
                    continue

                value_str = str(value)

                for issue in self.ENCODING_ISSUES:
                    if issue in value_str:
                        errors.append(ValidationError(
                            row_index=idx,
                            column=col,
                            rule_id=self.metadata.id,
                            rule_name=self.metadata.name_de,
                            severity=self.metadata.severity,
                            message=f"Mögliches Kodierungsproblem: '{value_str[:50]}...' " if len(value_str) > 50 else f"Mögliches Kodierungsproblem: '{value_str}'",
                            value=value_str[:100],
                            suggestion="Prüfen Sie die Zeichenkodierung der Quelldatei (UTF-8 empfohlen)",
                        ))
                        break  # Only report once per cell

        return errors
