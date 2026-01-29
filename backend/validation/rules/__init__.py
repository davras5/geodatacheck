"""
Validation rules package.

Contains all built-in validation rules organized by category.
"""

from .address import (
    RequiredFieldsRule,
    PLZFormatRule,
    CantonValidationRule,
    StreetFormatRule,
)

from .coordinates import (
    CoordinatePresenceRule,
    SwissBoundsRule,
    CoordinatePrecisionRule,
)

from .egid import (
    EGIDFormatRule,
    EGIDUniquenessRule,
    EGIDPresenceRule,
)

from .general import (
    DuplicateRowsRule,
    EmptyRowsRule,
    DataTypeConsistencyRule,
    EncodingIssuesRule,
)

# All rules for easy registration
ALL_RULES = [
    # Address rules
    RequiredFieldsRule,
    PLZFormatRule,
    CantonValidationRule,
    StreetFormatRule,
    # Coordinate rules
    CoordinatePresenceRule,
    SwissBoundsRule,
    CoordinatePrecisionRule,
    # EGID rules
    EGIDFormatRule,
    EGIDUniquenessRule,
    EGIDPresenceRule,
    # General rules
    DuplicateRowsRule,
    EmptyRowsRule,
    DataTypeConsistencyRule,
    EncodingIssuesRule,
]

__all__ = [
    'RequiredFieldsRule',
    'PLZFormatRule',
    'CantonValidationRule',
    'StreetFormatRule',
    'CoordinatePresenceRule',
    'SwissBoundsRule',
    'CoordinatePrecisionRule',
    'EGIDFormatRule',
    'EGIDUniquenessRule',
    'EGIDPresenceRule',
    'DuplicateRowsRule',
    'EmptyRowsRule',
    'DataTypeConsistencyRule',
    'EncodingIssuesRule',
    'ALL_RULES',
]
