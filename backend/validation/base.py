"""
Base classes for the GeoDataCheck validation framework.

To create a new validation rule:
1. Create a class that inherits from BaseRule
2. Implement the metadata property with RuleMetadata
3. Implement the validate() method
4. Register the rule in the registry
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Dict
import pandas as pd


class Severity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """Categories for grouping validation rules."""
    ADDRESS = "address"
    COORDINATES = "coordinates"
    EGID = "egid"
    GENERAL = "general"
    CUSTOM = "custom"


@dataclass
class ValidationError:
    """Represents a single validation error/warning."""
    row_index: int
    column: str
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    value: Any = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'row_index': self.row_index,
            'row_number': self.row_index + 2,  # Excel row (1-indexed + header)
            'column': self.column,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'message': self.message,
            'value': str(self.value) if self.value is not None else None,
            'suggestion': self.suggestion,
        }


@dataclass
class RuleMetadata:
    """Metadata for a validation rule, used for documentation."""
    id: str
    name: str
    name_de: str  # German name
    description: str
    description_de: str  # German description
    category: Category
    severity: Severity
    required_columns: List[str] = field(default_factory=list)
    example_valid: Optional[str] = None
    example_invalid: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'name_de': self.name_de,
            'description': self.description,
            'description_de': self.description_de,
            'category': self.category.value,
            'severity': self.severity.value,
            'required_columns': self.required_columns,
            'example_valid': self.example_valid,
            'example_invalid': self.example_invalid,
        }


class BaseRule(ABC):
    """
    Base class for all validation rules.

    To create a new rule:

    ```python
    class MyRule(BaseRule):
        @property
        def metadata(self) -> RuleMetadata:
            return RuleMetadata(
                id="R-XXX-01",
                name="My Rule",
                name_de="Meine Regel",
                description="What this rule checks",
                description_de="Was diese Regel prüft",
                category=Category.GENERAL,
                severity=Severity.ERROR,
                required_columns=['column_name'],
            )

        def validate(self, df: pd.DataFrame, config: dict) -> List[ValidationError]:
            errors = []
            # Your validation logic here
            return errors
    ```
    """

    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Return rule metadata for documentation and UI."""
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate the dataframe and return list of errors.

        Args:
            df: The pandas DataFrame to validate
            config: Configuration dict with column mappings and options
                - columns: dict mapping logical names to actual column names
                - options: dict with rule-specific options

        Returns:
            List of ValidationError objects
        """
        pass

    def is_applicable(self, df: pd.DataFrame, config: Dict[str, Any]) -> bool:
        """
        Check if this rule should run based on available columns.

        Override this method for custom applicability logic.
        """
        columns = config.get('columns', {})
        for required in self.metadata.required_columns:
            actual_col = columns.get(required, required)
            if actual_col not in df.columns:
                return False
        return True

    def get_column(self, df: pd.DataFrame, config: Dict[str, Any], logical_name: str) -> Optional[str]:
        """
        Get the actual column name from config mapping.

        Args:
            df: The DataFrame
            config: Configuration with column mappings
            logical_name: The logical column name (e.g., 'plz', 'egid')

        Returns:
            The actual column name if it exists, None otherwise
        """
        columns = config.get('columns', {})
        actual_col = columns.get(logical_name, logical_name)
        if actual_col in df.columns:
            return actual_col
        # Try case-insensitive match
        for col in df.columns:
            if col.lower() == actual_col.lower():
                return col
        return None
