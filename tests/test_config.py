"""Unit tests for the ``.mdlintrc`` config loader, isolated from the CLI."""

import json

import pytest

from mdlint.config import ConfigError, load_enabled_rule_ids


def test_missing_file_returns_none(tmp_path):
    assert load_enabled_rule_ids(tmp_path / "nope.mdlintrc") is None


def test_object_without_enabled_key_returns_none(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({}))

    assert load_enabled_rule_ids(config) is None


def test_enabled_key_returns_its_list(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01", "MDT02"]}))

    assert load_enabled_rule_ids(config) == ["MDS01", "MDT02"]


def test_empty_enabled_list_is_returned_as_is(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": []}))

    assert load_enabled_rule_ids(config) == []


def test_invalid_json_raises_config_error_naming_the_path(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text("{not json")

    with pytest.raises(ConfigError, match=str(config)):
        load_enabled_rule_ids(config)


def test_non_object_json_raises_config_error(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps(["MDS01"]))

    with pytest.raises(ConfigError, match="expected a JSON object"):
        load_enabled_rule_ids(config)


def test_enabled_as_non_list_raises_config_error(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": "MDS01"}))

    with pytest.raises(ConfigError, match='"enabled" must be a list of rule id strings'):
        load_enabled_rule_ids(config)


def test_enabled_list_with_non_string_item_raises_config_error(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01", 2]}))

    with pytest.raises(ConfigError, match='"enabled" must be a list of rule id strings'):
        load_enabled_rule_ids(config)


def test_invalid_utf8_raises_config_error(tmp_path):
    config = tmp_path / ".mdlintrc"
    config.write_bytes(b"\xff\xfe\x00\x00bad")

    with pytest.raises(ConfigError, match=str(config)):
        load_enabled_rule_ids(config)


def test_directory_path_raises_config_error(tmp_path):
    config_dir = tmp_path / ".mdlintrc"
    config_dir.mkdir()

    with pytest.raises(ConfigError, match=str(config_dir)):
        load_enabled_rule_ids(config_dir)
