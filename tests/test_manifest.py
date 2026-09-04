"""Regression tests for `aegis.manifest.RuntimeConfig` validation.

These exist because the validation below was dead. `RuntimeConfig` declared its
mutual-exclusion rule in a method named `model_post_init__`, with a trailing
double underscore; pydantic's hook is `model_post_init`, so pydantic never called
it and every invalid runtime block was accepted. `hasattr(RuntimeConfig,
"model_post_init__")` was True and `"model_post_init" in vars(RuntimeConfig)` was
False, which is the shape of the defect in one line.

Each case is its own test rather than a clause in a shared one, so that a later
change that breaks one is visible on its own instead of being hidden behind an
earlier clause's failure.
"""

import pytest

from aegis.manifest import RuntimeConfig


def test_runtime_config_rejects_language_without_version() -> None:
    with pytest.raises(ValueError, match="language requires version to be specified"):
        RuntimeConfig(language="python")


def test_runtime_config_rejects_version_without_language() -> None:
    with pytest.raises(ValueError, match="version requires language to be specified"):
        RuntimeConfig(version="3.11")


def test_runtime_config_rejects_empty_runtime() -> None:
    with pytest.raises(
        ValueError,
        match="must specify either standard runtime",
    ):
        RuntimeConfig()


def test_runtime_config_rejects_unqualified_image() -> None:
    with pytest.raises(ValueError, match="image must be fully-qualified"):
        RuntimeConfig(image="nginx")


def test_runtime_config_rejects_both_modes_together() -> None:
    with pytest.raises(ValueError, match="cannot specify both image and language"):
        RuntimeConfig(language="python", version="3.11", image="ghcr.io/org/img:v1")


def test_runtime_config_rejects_blank_image() -> None:
    """A blank string is not None, so it reached the cross-field rule as "a custom
    runtime was specified" and failed with the fully-qualified-image message, which
    is not what is wrong with it."""
    with pytest.raises(ValueError, match="must not be blank"):
        RuntimeConfig(image="   ")


def test_runtime_config_rejects_blank_language() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        RuntimeConfig(language="", version="3.11")


def test_runtime_config_accepts_standard_runtime() -> None:
    """Control: the rule must not reject what it is supposed to allow."""
    cfg = RuntimeConfig(language="python", version="3.11")
    assert cfg.language == "python"
    assert cfg.version == "3.11"
    assert cfg.image is None


def test_runtime_config_accepts_custom_runtime() -> None:
    """Control."""
    cfg = RuntimeConfig(image="ghcr.io/org/image:v1.0")
    assert cfg.image == "ghcr.io/org/image:v1.0"
    assert cfg.language is None
