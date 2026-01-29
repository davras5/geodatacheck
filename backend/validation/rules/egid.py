"""
EGID (Eidgenössischer Gebäudeidentifikator) validation rules.
"""

from typing import List, Dict, Any, Set
import pandas as pd

from ..base import BaseRule, RuleMetadata, ValidationError, Category, Severity


class EGIDFormatRule(BaseRule):
    """Validates EGID format."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-EGID-01",
            name="EGID Format",
            name_de="EGID-Format",
            description="EGID must be a positive integer (federal building identifier)",
            description_de="EGID muss eine positive Ganzzahl sein (Eidgenössischer Gebäudeidentifikator)",
            category=Category.EGID,
            severity=Severity.ERROR,
            required_columns=['egid'],
            example_valid="123456789",
            example_invalid="12-345, EGID123, -500",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        egid_col = self.get_column(df, config, 'egid')

        if egid_col is None:
            return errors

        for idx, row in df.iterrows():
            value = row[egid_col]

            if pd.isna(value) or str(value).strip() == '':
                continue  # EGID might be optional

            try:
                # Handle float values like 123456.0 from Excel
                egid_str = str(value).strip()
                if '.' in egid_str:
                    egid = int(float(egid_str))
                else:
                    egid = int(egid_str)

                if egid <= 0:
                    errors.append(ValidationError(
                        row_index=idx,
                        column=egid_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"EGID muss positiv sein: '{value}'",
                        value=value,
                    ))
                elif egid > 999999999:  # EGIDs are typically 9 digits max
                    errors.append(ValidationError(
                        row_index=idx,
                        column=egid_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=Severity.WARNING,
                        message=f"EGID ungewöhnlich gross: '{value}'",
                        value=value,
                    ))

            except (ValueError, TypeError):
                errors.append(ValidationError(
                    row_index=idx,
                    column=egid_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"Ungültiges EGID-Format: '{value}' (muss eine Zahl sein)",
                    value=value,
                ))

        return errors


class EGIDUniquenessRule(BaseRule):
    """Checks for duplicate EGIDs in the dataset."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-EGID-02",
            name="EGID Uniqueness",
            name_de="EGID-Eindeutigkeit",
            description="Each EGID should appear only once (unless multiple units per building)",
            description_de="Jedes EGID sollte nur einmal vorkommen (ausser bei mehreren Einheiten pro Gebäude)",
            category=Category.EGID,
            severity=Severity.WARNING,
            required_columns=['egid'],
            example_valid="123, 456, 789 (alle unterschiedlich)",
            example_invalid="123, 123, 456 (123 doppelt)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        egid_col = self.get_column(df, config, 'egid')

        if egid_col is None:
            return errors

        # Track EGID occurrences
        egid_rows: Dict[str, List[int]] = {}

        for idx, row in df.iterrows():
            value = row[egid_col]

            if pd.isna(value) or str(value).strip() == '':
                continue

            # Normalize EGID (handle floats)
            try:
                egid_str = str(value).strip()
                if '.' in egid_str:
                    egid_key = str(int(float(egid_str)))
                else:
                    egid_key = egid_str
            except (ValueError, TypeError):
                continue  # Invalid format handled by format rule

            if egid_key not in egid_rows:
                egid_rows[egid_key] = []
            egid_rows[egid_key].append(idx)

        # Report duplicates
        for egid, rows in egid_rows.items():
            if len(rows) > 1:
                # Report on all but the first occurrence
                for idx in rows[1:]:
                    errors.append(ValidationError(
                        row_index=idx,
                        column=egid_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"EGID '{egid}' kommt mehrfach vor (Zeilen: {', '.join(str(r+2) for r in rows)})",
                        value=egid,
                        suggestion="Prüfen Sie, ob es sich um Duplikate oder verschiedene Einheiten handelt",
                    ))

        return errors


class EGIDPresenceRule(BaseRule):
    """Checks that EGID is provided for all records."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-EGID-03",
            name="EGID Presence",
            name_de="EGID vorhanden",
            description="Every building record should have an EGID",
            description_de="Jeder Gebäudedatensatz sollte eine EGID haben",
            category=Category.EGID,
            severity=Severity.ERROR,
            required_columns=['egid'],
            example_valid="123456789",
            example_invalid="(leer)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        egid_col = self.get_column(df, config, 'egid')

        if egid_col is None:
            return errors

        for idx, row in df.iterrows():
            value = row[egid_col]

            if pd.isna(value) or str(value).strip() == '':
                errors.append(ValidationError(
                    row_index=idx,
                    column=egid_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message="EGID fehlt",
                    value=None,
                ))

        return errors
