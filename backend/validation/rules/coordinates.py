"""
Coordinate validation rules for Swiss coordinate systems (LV95, WGS84).
"""

from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import math

from ..base import BaseRule, RuleMetadata, ValidationError, Category, Severity


# Switzerland bounds
# LV95 (Swiss national coordinate system)
CH_BOUNDS_LV95 = {
    'e_min': 2485000, 'e_max': 2834000,  # Easting
    'n_min': 1075000, 'n_max': 1296000   # Northing
}

# WGS84 (GPS coordinates)
CH_BOUNDS_WGS84 = {
    'lon_min': 5.9, 'lon_max': 10.5,     # Longitude (E)
    'lat_min': 45.8, 'lat_max': 47.9     # Latitude (N)
}


def detect_coordinate_system(e: float, n: float) -> Optional[str]:
    """
    Detect if coordinates are LV95 or WGS84 based on value ranges.

    Returns 'LV95', 'WGS84', or None if unclear.
    """
    # LV95 has very large numbers (millions)
    if 2000000 < e < 3000000 and 1000000 < n < 2000000:
        return 'LV95'
    # WGS84 has small decimal numbers
    elif 5 < e < 11 and 45 < n < 48:
        return 'WGS84'
    return None


class CoordinatePresenceRule(BaseRule):
    """Checks that coordinates are provided."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-COORD-01",
            name="Coordinate Presence",
            name_de="Koordinaten vorhanden",
            description="Checks that both E and N coordinates are provided",
            description_de="Prüft, ob E- und N-Koordinaten vorhanden sind",
            category=Category.COORDINATES,
            severity=Severity.WARNING,
            required_columns=['easting', 'northing'],
            example_valid="E: 2600000, N: 1200000",
            example_invalid="E: 2600000, N: (leer)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        e_col = self.get_column(df, config, 'easting')
        n_col = self.get_column(df, config, 'northing')

        if e_col is None or n_col is None:
            return errors

        for idx, row in df.iterrows():
            e_val = row[e_col]
            n_val = row[n_col]

            e_missing = pd.isna(e_val) or str(e_val).strip() == ''
            n_missing = pd.isna(n_val) or str(n_val).strip() == ''

            if e_missing and not n_missing:
                errors.append(ValidationError(
                    row_index=idx,
                    column=e_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message="E-Koordinate fehlt (N-Koordinate vorhanden)",
                    value=None,
                ))
            elif n_missing and not e_missing:
                errors.append(ValidationError(
                    row_index=idx,
                    column=n_col,
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message="N-Koordinate fehlt (E-Koordinate vorhanden)",
                    value=None,
                ))

        return errors


class SwissBoundsRule(BaseRule):
    """Validates coordinates are within Switzerland."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-COORD-02",
            name="Swiss Bounds Check",
            name_de="Schweizer Grenzen",
            description="Coordinates must fall within Switzerland's boundaries",
            description_de="Koordinaten müssen innerhalb der Schweizer Grenzen liegen",
            category=Category.COORDINATES,
            severity=Severity.ERROR,
            required_columns=['easting', 'northing'],
            example_valid="E: 2600000, N: 1200000 (Bern, LV95)",
            example_invalid="E: 1000000, N: 500000 (ausserhalb CH)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        e_col = self.get_column(df, config, 'easting')
        n_col = self.get_column(df, config, 'northing')

        if e_col is None or n_col is None:
            return errors

        coord_system = config.get('options', {}).get('coordinate_system', 'auto')

        for idx, row in df.iterrows():
            e_val = row[e_col]
            n_val = row[n_col]

            if pd.isna(e_val) or pd.isna(n_val):
                continue

            try:
                e = float(e_val)
                n = float(n_val)
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    row_index=idx,
                    column=f"{e_col}/{n_col}",
                    rule_id=self.metadata.id,
                    rule_name=self.metadata.name_de,
                    severity=self.metadata.severity,
                    message=f"Ungültige Koordinatenwerte: E={e_val}, N={n_val}",
                    value=f"E={e_val}, N={n_val}",
                ))
                continue

            # Auto-detect coordinate system if needed
            if coord_system == 'auto':
                detected = detect_coordinate_system(e, n)
                if detected is None:
                    errors.append(ValidationError(
                        row_index=idx,
                        column=f"{e_col}/{n_col}",
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"Koordinatensystem nicht erkennbar: E={e}, N={n}",
                        value=f"E={e}, N={n}",
                    ))
                    continue
                system = detected
            else:
                system = coord_system

            # Check bounds based on system
            if system == 'LV95':
                bounds = CH_BOUNDS_LV95
                if not (bounds['e_min'] <= e <= bounds['e_max']):
                    errors.append(ValidationError(
                        row_index=idx,
                        column=e_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"E-Koordinate ausserhalb Schweiz: {e} (LV95: {bounds['e_min']}-{bounds['e_max']})",
                        value=e,
                    ))
                if not (bounds['n_min'] <= n <= bounds['n_max']):
                    errors.append(ValidationError(
                        row_index=idx,
                        column=n_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"N-Koordinate ausserhalb Schweiz: {n} (LV95: {bounds['n_min']}-{bounds['n_max']})",
                        value=n,
                    ))
            else:  # WGS84
                bounds = CH_BOUNDS_WGS84
                if not (bounds['lon_min'] <= e <= bounds['lon_max']):
                    errors.append(ValidationError(
                        row_index=idx,
                        column=e_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"Longitude ausserhalb Schweiz: {e} (WGS84: {bounds['lon_min']}-{bounds['lon_max']})",
                        value=e,
                    ))
                if not (bounds['lat_min'] <= n <= bounds['lat_max']):
                    errors.append(ValidationError(
                        row_index=idx,
                        column=n_col,
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"Latitude ausserhalb Schweiz: {n} (WGS84: {bounds['lat_min']}-{bounds['lat_max']})",
                        value=n,
                    ))

        return errors


class CoordinatePrecisionRule(BaseRule):
    """Checks coordinate precision is appropriate."""

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="R-COORD-04",
            name="Coordinate Precision",
            name_de="Koordinaten-Präzision",
            description="Checks that coordinates have appropriate precision for building location",
            description_de="Prüft, ob Koordinaten ausreichende Präzision für Gebäudestandort haben",
            category=Category.COORDINATES,
            severity=Severity.WARNING,
            required_columns=['easting', 'northing'],
            example_valid="E: 2600123.45, N: 1200456.78",
            example_invalid="E: 2600000, N: 1200000 (zu rund)",
        )

    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        e_col = self.get_column(df, config, 'easting')
        n_col = self.get_column(df, config, 'northing')

        if e_col is None or n_col is None:
            return errors

        for idx, row in df.iterrows():
            e_val = row[e_col]
            n_val = row[n_col]

            if pd.isna(e_val) or pd.isna(n_val):
                continue

            try:
                e = float(e_val)
                n = float(n_val)
            except (ValueError, TypeError):
                continue  # Handled by other rules

            # Detect system
            system = detect_coordinate_system(e, n)
            if system is None:
                continue

            # For LV95, check if coordinates are suspiciously round
            if system == 'LV95':
                # If both end in 000, likely imprecise
                if e % 1000 == 0 and n % 1000 == 0:
                    errors.append(ValidationError(
                        row_index=idx,
                        column=f"{e_col}/{n_col}",
                        rule_id=self.metadata.id,
                        rule_name=self.metadata.name_de,
                        severity=self.metadata.severity,
                        message=f"Koordinaten ungewöhnlich rund (auf 1000m): E={e}, N={n}",
                        value=f"E={e}, N={n}",
                        suggestion="Koordinaten könnten ungenau oder gerundet sein",
                    ))

        return errors
