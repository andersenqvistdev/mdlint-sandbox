"""Tests for the mdlint command-line entry point."""

import json
import os
import sys

import pytest

from mdlint.cli import main

needs_unix_perms = pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="permission bits are not enforceable on Windows or as root",
)


def test_clean_file_exits_zero_with_no_output(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n## Section\n")

    exit_code = main([str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_file_with_violations_exits_one_and_prints_each_in_order(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n# Title\n### Too deep\n")

    exit_code = main([str(doc)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert len(lines) == 2
    assert lines[0].startswith(f"{doc}:1: MDS01")
    assert lines[1].startswith(f"{doc}:3: MDS02")


def test_multiple_files_mixed_clean_and_dirty(tmp_path, capsys):
    clean = tmp_path / "clean.md"
    clean.write_text("# Title\n")
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    exit_code = main([str(clean), str(dirty)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert len(lines) == 1
    assert lines[0] == f"{dirty}:1: MDS01 first line should be a top-level (H1) heading"


def test_nonexistent_file_exits_two_with_stderr_message(tmp_path, capsys):
    missing = tmp_path / "missing.md"

    exit_code = main([str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(missing) in captured.err
    assert captured.out == ""


def test_read_error_takes_priority_over_violations(tmp_path, capsys):
    missing = tmp_path / "missing.md"
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    exit_code = main([str(missing), str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(missing) in captured.err
    assert f"{dirty}:1: MDS01" in captured.out


def test_directory_passed_as_file_exits_two_with_stderr_message(tmp_path, capsys):
    a_directory = tmp_path / "not-a-file"
    a_directory.mkdir()

    exit_code = main([str(a_directory)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(a_directory) in captured.err
    assert captured.out == ""


@needs_unix_perms
def test_unreadable_file_exits_two_with_stderr_message(tmp_path, capsys):
    unreadable = tmp_path / "secret.md"
    unreadable.write_text("# Title\n")
    unreadable.chmod(0o000)

    try:
        exit_code = main([str(unreadable)])
    finally:
        unreadable.chmod(0o644)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(unreadable) in captured.err
    assert captured.out == ""


@needs_unix_perms
def test_unreadable_file_does_not_stop_remaining_files_from_being_linted(tmp_path, capsys):
    unreadable = tmp_path / "secret.md"
    unreadable.write_text("# Title\n")
    unreadable.chmod(0o000)
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    try:
        exit_code = main([str(unreadable), str(dirty)])
    finally:
        unreadable.chmod(0o644)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(unreadable) in captured.err
    assert f"{dirty}:1: MDS01" in captured.out


@needs_unix_perms
def test_fix_continues_past_an_unwritable_file(tmp_path, capsys):
    unwritable = tmp_path / "doc.md"
    unwritable.write_text("Not a heading\n\n- one\n* two\n")
    unwritable.chmod(0o400)
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n\n- one\n* two\n")

    try:
        exit_code = main(["--fix", str(unwritable), str(dirty)])
    finally:
        unwritable.chmod(0o600)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(unwritable) in captured.err
    # The remaining file must still be fixed, proving the run didn't abort.
    assert dirty.read_text() == "Not a heading\n\n- one\n- two\n"
    # The write failed, so the file on disk is still unfixed: it must be
    # linted against its real (unfixed) content, not silently dropped.
    assert unwritable.read_text() == "Not a heading\n\n- one\n* two\n"
    assert f"{unwritable}:1: MDS01" in captured.out


def test_exact_output_line_format(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")

    exit_code = main([str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == f"{doc}:1: MDS01 first line should be a top-level (H1) heading\n"


def test_fix_rewrites_the_file_and_reports_remaining_violations(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n- one\n* two\n")

    exit_code = main(["--fix", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert doc.read_text() == "# Title\n\n- one\n- two\n"


def test_fix_leaves_unfixable_violations_in_place(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")

    exit_code = main(["--fix", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MDS01" in captured.out
    assert doc.read_text() == "Not a heading\n"


def test_fix_does_not_rewrite_a_clean_file(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    original_mtime = doc.stat().st_mtime_ns

    exit_code = main(["--fix", str(doc)])

    assert exit_code == 0
    assert doc.stat().st_mtime_ns == original_mtime


def test_format_json_reports_violations_as_structured_data(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")

    exit_code = main(["--format", "json", str(doc)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["errors"] == []
    assert payload["violations"] == [
        {
            "file": str(doc),
            "line": 1,
            "rule_id": "MDS01",
            "message": "first line should be a top-level (H1) heading",
        }
    ]


def test_format_json_reports_read_errors(tmp_path, capsys):
    missing = tmp_path / "missing.md"

    exit_code = main(["--format", "json", str(missing)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert payload["violations"] == []
    assert payload["errors"][0]["file"] == str(missing)


def test_format_json_clean_file_is_an_empty_result(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")

    exit_code = main(["--format", "json", str(doc)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload == {"violations": [], "errors": []}


def test_ignore_skips_matching_files(tmp_path, capsys):
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    exit_code = main(["--ignore", "dirty.md", str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_ignore_glob_pattern_matches_by_basename(tmp_path, capsys):
    dirty = tmp_path / "draft-notes.md"
    dirty.write_text("Not a heading\n")

    exit_code = main(["--ignore", "draft-*.md", str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_ignore_does_not_affect_non_matching_files(tmp_path, capsys):
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    exit_code = main(["--ignore", "other.md", str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert str(dirty) in captured.out


def test_ignore_glob_pattern_matches_full_path_in_subdirectory(tmp_path, capsys, monkeypatch):
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "dirty.md").write_text("Not a heading\n")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--ignore", "vendor/*", "vendor/dirty.md"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_multiple_ignore_flags_each_skip_their_matching_file(tmp_path, capsys):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("Not a heading\n")
    draft = tmp_path / "draft-notes.md"
    draft.write_text("Not a heading\n")
    kept = tmp_path / "kept.md"
    kept.write_text("Not a heading\n")

    exit_code = main(
        [
            "--ignore",
            "CHANGELOG.md",
            "--ignore",
            "draft-*.md",
            str(changelog),
            str(draft),
            str(kept),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert str(kept) in captured.out
    assert str(changelog) not in captured.out
    assert str(draft) not in captured.out


def test_config_restricts_enabled_rules(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n# Title\n### Too deep\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS02"]}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert len(lines) == 1
    assert "MDS02" in lines[0]


def test_config_with_no_enabled_key_runs_every_rule(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MDS01" in captured.out


def test_missing_config_file_runs_every_rule(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")

    exit_code = main(["--config", str(tmp_path / "nope.mdlintrc"), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MDS01" in captured.out


def test_invalid_config_json_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text("{not json")

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err


def test_default_config_is_discovered_in_the_current_directory(tmp_path, capsys, monkeypatch):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n# Title\n### Too deep\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS02"]}))
    monkeypatch.chdir(tmp_path)

    exit_code = main(["doc.md"])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert len(lines) == 1
    assert "MDS02" in lines[0]


def test_config_that_is_not_a_json_object_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps(["MDS01"]))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err


def test_config_with_unknown_rule_id_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01", "MDS99"]}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err
    assert "MDS99" in captured.err


def test_config_path_that_is_a_directory_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config_dir = tmp_path / ".mdlintrc"
    config_dir.mkdir()

    exit_code = main(["--config", str(config_dir), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config_dir) in captured.err
    assert captured.out == ""


def test_config_with_invalid_utf8_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_bytes(b"\xff\xfe\x00\x00bad")

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err
    assert captured.out == ""


def test_config_with_non_list_enabled_value_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": "MDS01"}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err


def test_fix_only_applies_fixes_for_rules_enabled_by_config(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n- one\n* two\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01"]}))

    exit_code = main(["--fix", "--config", str(config), str(doc)])

    assert exit_code == 0
    # MDT01's fix would normalize "* two" to "- two", but MDT01 is disabled
    # by the config, so the file must be left untouched.
    assert doc.read_text() == "# Title\n\n- one\n* two\n"


def test_fix_and_format_json_report_remaining_violations_after_fixing(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n\n- one\n* two\n")

    exit_code = main(["--fix", "--format", "json", str(doc)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert doc.read_text() == "Not a heading\n\n- one\n- two\n"
    assert payload["errors"] == []
    assert payload["violations"] == [
        {
            "file": str(doc),
            "line": 1,
            "rule_id": "MDS01",
            "message": "first line should be a top-level (H1) heading",
        }
    ]


def test_fix_config_format_and_ignore_flags_all_combine_correctly(tmp_path, capsys):
    kept = tmp_path / "doc.md"
    kept.write_text("# Title\n\n- one\n* two\n")
    ignored = tmp_path / "vendor.md"
    ignored.write_text("Not a heading\n\n- one\n* two\n")
    config = tmp_path / ".mdlintrc"
    # MDS01 stays enabled so the doc's remaining violation still surfaces;
    # MDT01 is left out so its autofix must not run on either file.
    config.write_text(json.dumps({"enabled": ["MDS01", "MDT01"]}))

    exit_code = main(
        [
            "--fix",
            "--format",
            "json",
            "--config",
            str(config),
            "--ignore",
            "vendor.md",
            str(kept),
            str(ignored),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    # --ignore excluded vendor.md from every stage: it was neither fixed...
    assert ignored.read_text() == "Not a heading\n\n- one\n* two\n"
    # ...nor linted, so it contributes no violations despite being dirty.
    assert payload == {"violations": [], "errors": []}
    # The non-ignored file went through --fix with only the config-enabled
    # rules (MDT01's "* two" -> "- two" fix ran; MDS01 had nothing to fix).
    assert kept.read_text() == "# Title\n\n- one\n- two\n"
