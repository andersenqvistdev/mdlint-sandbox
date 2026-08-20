"""Tests for the mdlint command-line entry point."""

import json

from mdlint.cli import main


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


def test_config_that_is_not_a_json_object_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps(["MDS01"]))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err


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
