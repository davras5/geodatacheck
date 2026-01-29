"""
GeoDataCheck Validation Framework

A modular Python framework for validating geodata, particularly Swiss
building and address data including EGID, coordinates, and addresses.

Usage:
    from validation import create_default_registry, ValidationEngine

    # Create engine with all default rules
    registry = create_default_registry()
    engine = ValidationEngine(registry)

    # Load and validate data
    import pandas as pd
    df = pd.read_excel('buildings.xlsx')

    config = {
        'columns': engine.detect_columns(df),
        'options': {}
    }

    result = engine.validate(df, config)

    print(f"Total rows: {result.total_rows}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")
"""

from .base import (
    BaseRule,
    RuleMetadata,
    ValidationError,
    Category,
    Severity,
)

from .engine import (
    RuleRegistry,
    ValidationEngine,
    ValidationResult,
)

from .rules import ALL_RULES


def create_default_registry() -> RuleRegistry:
    """
    Create a rule registry with all default validation rules.

    Returns:
        RuleRegistry with all built-in rules registered
    """
    registry = RuleRegistry()

    for rule_class in ALL_RULES:
        registry.register(rule_class())

    return registry


__all__ = [
    # Base classes
    'BaseRule',
    'RuleMetadata',
    'ValidationError',
    'Category',
    'Severity',
    # Engine
    'RuleRegistry',
    'ValidationEngine',
    'ValidationResult',
    # Factory
    'create_default_registry',
]
