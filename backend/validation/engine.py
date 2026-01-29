"""
Validation engine - orchestrates rule execution and aggregates results.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
from collections import defaultdict

from .base import BaseRule, ValidationError, Category, Severity, RuleMetadata


class RuleRegistry:
    """Central registry for all validation rules."""

    def __init__(self):
        self._rules: Dict[str, BaseRule] = {}

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

    def get_rule_ids(self) -> List[str]:
        """Get all rule IDs."""
        return list(self._rules.keys())

    def get_documentation(self) -> List[dict]:
        """Generate documentation for all rules."""
        return [
            r.metadata.to_dict()
            for r in sorted(self._rules.values(), key=lambda x: x.metadata.id)
        ]


@dataclass
class ValidationResult:
    """Complete result of a validation run."""
    total_rows: int
    errors: List[ValidationError] = field(default_factory=list)
    rules_executed: List[str] = field(default_factory=list)
    rules_skipped: List[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.INFO)

    @property
    def passed_rows(self) -> int:
        error_rows = set(e.row_index for e in self.errors if e.severity == Severity.ERROR)
        return self.total_rows - len(error_rows)

    def get_errors_by_category(self) -> Dict[str, int]:
        """Group error counts by rule category."""
        counts = defaultdict(int)
        for e in self.errors:
            # Extract category from rule_id (e.g., R-ADDR-01 -> ADDRESS)
            parts = e.rule_id.split('-')
            if len(parts) >= 2:
                cat_map = {'ADDR': 'address', 'COORD': 'coordinates',
                          'EGID': 'egid', 'GEN': 'general', 'CUSTOM': 'custom'}
                cat = cat_map.get(parts[1], 'general')
                counts[cat] += 1
        return dict(counts)

    def get_errors_by_rule(self) -> Dict[str, int]:
        """Group error counts by rule."""
        counts = defaultdict(int)
        for e in self.errors:
            counts[e.rule_id] += 1
        return dict(counts)

    def get_errors_by_dimension(self, df: pd.DataFrame, dimension_col: str) -> Dict[str, Dict[str, int]]:
        """
        Group errors by a dimension column (e.g., region, portfolio).

        Returns dict like:
        {
            'Zürich': {'total': 100, 'errors': 5, 'warnings': 10},
            'Bern': {'total': 80, 'errors': 2, 'warnings': 3},
        }
        """
        if dimension_col not in df.columns:
            return {}

        result = defaultdict(lambda: {'total': 0, 'errors': 0, 'warnings': 0})

        # Count total rows per dimension
        for idx, row in df.iterrows():
            dim_value = str(row[dimension_col]) if pd.notna(row[dimension_col]) else '(leer)'
            result[dim_value]['total'] += 1

        # Count errors per dimension
        for error in self.errors:
            if error.row_index < len(df):
                dim_value = df.iloc[error.row_index][dimension_col]
                dim_value = str(dim_value) if pd.notna(dim_value) else '(leer)'
                if error.severity == Severity.ERROR:
                    result[dim_value]['errors'] += 1
                elif error.severity == Severity.WARNING:
                    result[dim_value]['warnings'] += 1

        return dict(result)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_rows': self.total_rows,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'passed_rows': self.passed_rows,
            'pass_rate': round(self.passed_rows / self.total_rows * 100, 1) if self.total_rows > 0 else 100,
            'errors': [e.to_dict() for e in self.errors],
            'errors_by_category': self.get_errors_by_category(),
            'errors_by_rule': self.get_errors_by_rule(),
            'rules_executed': self.rules_executed,
            'rules_skipped': self.rules_skipped,
        }


class ValidationEngine:
    """
    Orchestrates validation rule execution.

    Usage:
        registry = RuleRegistry()
        registry.register(PLZFormatRule())
        registry.register(SwissBoundsRule())

        engine = ValidationEngine(registry)
        result = engine.validate(df, config)
    """

    def __init__(self, registry: RuleRegistry):
        self.registry = registry

    def validate(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        rule_ids: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Run validation rules against the dataframe.

        Args:
            df: The pandas DataFrame to validate
            config: Configuration with column mappings and options
            rule_ids: Optional list of specific rule IDs to run (None = all)

        Returns:
            ValidationResult with all errors and statistics
        """
        result = ValidationResult(total_rows=len(df))

        # Get rules to execute
        if rule_ids:
            rules = [self.registry.get_rule(rid) for rid in rule_ids]
            rules = [r for r in rules if r is not None]
        else:
            rules = self.registry.get_all_rules()

        # Execute each rule
        for rule in rules:
            if rule.is_applicable(df, config):
                try:
                    errors = rule.validate(df, config)
                    result.errors.extend(errors)
                    result.rules_executed.append(rule.metadata.id)
                except Exception as e:
                    # Log error but continue with other rules
                    print(f"Error executing rule {rule.metadata.id}: {e}")
                    result.rules_skipped.append(rule.metadata.id)
            else:
                result.rules_skipped.append(rule.metadata.id)

        return result

    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Auto-detect column mappings based on common naming patterns.

        Returns dict mapping logical names to detected column names.
        """
        patterns = {
            'plz': ['plz', 'postleitzahl', 'postal_code', 'zip', 'npa'],
            'ort': ['ort', 'stadt', 'gemeinde', 'city', 'town', 'locality', 'ortschaft'],
            'strasse': ['strasse', 'street', 'adresse', 'address', 'str', 'rue'],
            'hausnummer': ['hausnummer', 'hausnr', 'nr', 'number', 'no'],
            'kanton': ['kanton', 'kt', 'canton', 'state', 'ct'],
            'egid': ['egid', 'gebäude_id', 'building_id', 'geb_id', 'egid_edid'],
            'ewid': ['ewid', 'wohnung_id', 'dwelling_id'],
            'easting': ['e', 'e_coord', 'x', 'x_coord', 'easting', 'lon', 'longitude', 'e_lv95', 'koordinate_e'],
            'northing': ['n', 'n_coord', 'y', 'y_coord', 'northing', 'lat', 'latitude', 'n_lv95', 'koordinate_n'],
            'region': ['region', 'gebiet', 'zone', 'area'],
            'portfolio': ['portfolio', 'portfolio_typ', 'kategorie', 'type', 'asset_type', 'objekttyp'],
            'responsible': ['verantwortlich', 'zuständig', 'owner', 'responsible', 'bearbeiter', 'sachbearbeiter'],
        }

        detected = {}
        df_cols_lower = {col.lower(): col for col in df.columns}

        for logical_name, possible_names in patterns.items():
            for name in possible_names:
                if name in df_cols_lower:
                    detected[logical_name] = df_cols_lower[name]
                    break

        return detected
