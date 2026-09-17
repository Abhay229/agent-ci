"""Optional AI-assisted test generation."""

from agent_ci.testgen.config import is_test_generation_enabled
from agent_ci.testgen.generator import generate_tests_for_regression, generate_tests_for_report
from agent_ci.testgen.store import GeneratedTestStore, get_generated_test_store
from agent_ci.testgen.types import AI_TEST_DISCLAIMER
from agent_ci.testgen.validator import validate_generated_test

__all__ = [
    "AI_TEST_DISCLAIMER",
    "GeneratedTestStore",
    "generate_tests_for_regression",
    "generate_tests_for_report",
    "get_generated_test_store",
    "is_test_generation_enabled",
    "validate_generated_test",
]
