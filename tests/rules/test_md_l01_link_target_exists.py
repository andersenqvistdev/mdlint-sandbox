"""Tests for MDL01 — relative link targets must exist on disk."""

from mdlint.rules.md_l01_link_target_exists import RULE_ID, check


def test_passes_when_relative_target_exists(tmp_path):
    (tmp_path / "other.md").write_text("# Other\n")
    doc = tmp_path / "doc.md"
    lines = ["[link](other.md)"]

    assert check(str(doc), lines) == []


def test_fails_when_relative_target_is_missing(tmp_path):
    doc = tmp_path / "doc.md"
    lines = ["[link](missing.md)"]

    violations = check(str(doc), lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_resolves_relative_target_against_the_document_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "target.md").write_text("# Target\n")
    doc = tmp_path / "sub" / "doc.md"
    lines = ["[link](target.md)"]

    assert check(str(doc), lines) == []


def test_strips_fragment_before_checking_existence(tmp_path):
    (tmp_path / "other.md").write_text("# Other\n")
    doc = tmp_path / "doc.md"
    lines = ["[link](other.md#section)"]

    assert check(str(doc), lines) == []


def test_ignores_same_document_anchor_only_targets(tmp_path):
    doc = tmp_path / "doc.md"
    lines = ["[link](#section)"]

    assert check(str(doc), lines) == []


def test_ignores_external_urls(tmp_path):
    doc = tmp_path / "doc.md"
    lines = ["[link](https://example.com/missing)", "[email](mailto:a@example.com)"]

    assert check(str(doc), lines) == []


def test_ignores_absolute_paths(tmp_path):
    doc = tmp_path / "doc.md"
    lines = ["[link](/definitely/missing.md)"]

    assert check(str(doc), lines) == []


def test_checks_image_targets_too(tmp_path):
    doc = tmp_path / "doc.md"
    lines = ["![alt](missing.png)"]

    violations = check(str(doc), lines)

    assert len(violations) == 1
    assert violations[0].line == 1
