"""
Address validation rules for Swiss addresses.
"""

from typing import List, Dict, Any
import pandas as pd
import re

from ..base import BaseRule, RuleMetadata, ValidationError, Category, Severity


# Valid Swiss canton abbreviations
SWISS_CANTONS = {
    'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR',
    'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG',
    'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH'
}


class RequiredFieldsRule(BaseRule):
    """Checks that required address fields are present."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-ADDR-01",
            name="Required Fields",
            name_de="Pflichtfelder",
            description="Checks that essential address fields (street, PLZ, city) are not empty",
            description_de="Prüft, ob wesentliche Adressfelder (Strasse, PLZ, Ort) ausgefüllt sind",
            category=Category.ADDRESS,
            severity=Severity.ERROR,
            required_columns=[],  # Dynamic based on config
            example_valid="Bundesplatz 1, 3003, Bern",
            example_invalid="Bundesplatz 1, , (PLZ und Ort fehlen)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        columns = config.get('columns', {})

        # Check each required field
        required_fields = [
            ('plz', 'PLZ'),
            ('ort', 'Ort'),
            ('strasse', 'Strasse'),
        ]

        for logical_name, display_name in required_fields:
            col = self.get_column(df, config, logical_name)
            if col is None:
                continue  # Column not mapped, skip

            for idx, row in df.iterrows():
                value = row[col]
                if pd.isna(value) or str(value).strip() == '':
                    errors.append(ValidationError(
                        row_index=idx,
                        column=col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"{display_name} fehlt oder ist leer",
                        value=value,
                    ))

        return errors


class PLZFormatRule(BaseRule):
    """Validates Swiss postal code format."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-ADDR-02",
            name="PLZ Format",
            name_de="PLZ-Format",
            description="Swiss postal codes must be 4 digits between 1000 and 9999",
            description_de="Schweizer Postleitzahlen müssen 4-stellig sein (1000-9999)",
            category=Category.ADDRESS,
            severity=Severity.ERROR,
            required_columns=['plz'],
            example_valid="8001",
            example_invalid="123, 00100, 8001a",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        plz_col = self.get_column(df, config, 'plz')

        if plz_col is None:
            return errors

        for idx, row in df.iterrows():
            value = row[plz_col]

            if pd.isna(value) or str(value).strip() == '':
                continue  # Handled by required fields rule

            # Convert to string and clean
            plz_str = str(value).strip()

            # Handle float values like 8001.0
            if '.' in plz_str:
                try:
                    plz_str = str(int(float(plz_str)))
                except ValueError:
                    pass

            if not plz_str.isdigit():
                errors.append(ValidationError(
                    row_index=idx,
                    column=plz_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"PLZ muss numerisch sein: '{value}'",
                    value=value,
                ))
            elif len(plz_str) != 4:
                errors.append(ValidationError(
                    row_index=idx,
                    column=plz_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"PLZ muss 4-stellig sein: '{value}' ({len(plz_str)} Stellen)",
                    value=value,
                ))
            elif not (1000 <= int(plz_str) <= 9999):
                errors.append(ValidationError(
                    row_index=idx,
                    column=plz_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"PLZ ausserhalb gültiger Bereich: '{value}' (muss 1000-9999 sein)",
                    value=value,
                ))

        return errors


class CantonValidationRule(BaseRule):
    """Validates Swiss canton abbreviations."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-ADDR-04",
            name="Canton Validation",
            name_de="Kanton-Validierung",
            description="Canton abbreviation must be a valid Swiss canton (AG, BE, ZH, etc.)",
            description_de="Kantonsabkürzung muss ein gültiger Schweizer Kanton sein (AG, BE, ZH, etc.)",
            category=Category.ADDRESS,
            severity=Severity.ERROR,
            required_columns=['kanton'],
            example_valid="ZH, BE, VD",
            example_invalid="XX, Switzerland, Zürich",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        kanton_col = self.get_column(df, config, 'kanton')

        if kanton_col is None:
            return errors

        for idx, row in df.iterrows():
            value = row[kanton_col]

            if pd.isna(value) or str(value).strip() == '':
                continue  # Optional field

            kanton = str(value).strip().upper()

            if kanton not in SWISS_CANTONS:
                errors.append(ValidationError(
                    row_index=idx,
                    column=kanton_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"Ungültige Kantonsabkürzung: '{value}'",
                    value=value,
                    suggestion=f"Gültige Kantone: {', '.join(sorted(SWISS_CANTONS))}",
                ))

        return errors


class StreetFormatRule(BaseRule):
    """Checks street name format for obvious issues."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-ADDR-05",
            name="Street Format",
            name_de="Strassenformat",
            description="Checks street names for obvious formatting issues",
            description_de="Prüft Strassennamen auf offensichtliche Formatierungsfehler",
            category=Category.ADDRESS,
            severity=Severity.WARNING,
            required_columns=['strasse'],
            example_valid="Bundesplatz 1, Bahnhofstrasse 23a",
            example_invalid="123456, ????",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        strasse_col = self.get_column(df, config, 'strasse')

        if strasse_col is None:
            return errors

        for idx, row in df.iterrows():
            value = row[strasse_col]

            if pd.isna(value) or str(value).strip() == '':
                continue

            strasse = str(value).strip()

            # Check for all-numeric (likely wrong column)
            if strasse.isdigit():
                errors.append(ValidationError(
                    row_index=idx,
                    column=strasse_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=Severity.WARNING,
                    message=f"Strasse ist nur numerisch: '{value}'",
                    value=value,
                ))

            # Check for very short names (likely incomplete)
            elif len(strasse) < 3:
                errors.append(ValidationError(
                    row_index=idx,
                    column=strasse_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=Severity.WARNING,
                    message=f"Strassenname sehr kurz: '{value}'",
                    value=value,
                ))

            # Check for special characters that shouldn't be there
            elif re.search(r'[<>{}|\\^~\[\]]', strasse):
                errors.append(ValidationError(
                    row_index=idx,
                    column=strasse_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=Severity.WARNING,
                    message=f"Strassenname enthält ungewöhnliche Zeichen: '{value}'",
                    value=value,
                ))

        return errors
