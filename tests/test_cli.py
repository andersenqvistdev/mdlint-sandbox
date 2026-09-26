"""Tests for the mdlint command-line entry point."""

import json
import os
import shutil
import subprocess
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


def test_invalid_utf8_file_exits_two_with_stderr_message(tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"# Title\n\xff\xfe not valid utf-8\n")

    exit_code = main([str(bad)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(bad) in captured.err
    assert captured.out == ""


def test_invalid_utf8_file_is_reported_in_json_errors(tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"# Title\n\xff\xfe not valid utf-8\n")

    exit_code = main(["--format", "json", str(bad)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert payload["violations"] == []
    assert payload["errors"][0]["file"] == str(bad)


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


@needs_unix_perms
def test_fix_write_failure_is_reported_in_json_errors(tmp_path, capsys):
    unwritable = tmp_path / "doc.md"
    unwritable.write_text("Not a heading\n\n- one\n* two\n")
    unwritable.chmod(0o400)

    try:
        exit_code = main(["--fix", "--format", "json", str(unwritable)])
    finally:
        unwritable.chmod(0o600)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    # The write failure must surface in the structured "errors" list, not
    # just on stderr, since --format json callers don't read stderr.
    assert payload["errors"] == [
        {"file": str(unwritable), "message": payload["errors"][0]["message"]}
    ]
    # The file is still linted against its real (unfixed) content, so both
    # the unfixable MDS01 violation and the never-applied MDT01 autofix
    # still show up.
    assert payload["violations"] == [
        {
            "file": str(unwritable),
            "line": 1,
            "rule_id": "MDS01",
            "message": "first line should be a top-level (H1) heading",
        },
        {
            "file": str(unwritable),
            "line": 4,
            "rule_id": "MDT01",
            "message": "list marker '*' is inconsistent; file uses '-'",
        },
    ]


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


def test_fix_cleans_up_trailing_spaces_and_blank_line_runs(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title  \n\n\n\nBody.\n\n\n")

    exit_code = main(["--fix", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert doc.read_text() == "# Title\n\nBody.\n"


def test_mdt02_and_mdt03_violations_are_reported_through_the_cli(tmp_path, capsys):
    """MDT01 gets CLI-level coverage above; MDT02 and MDT03 were only ever
    exercised via their own rule-level unit tests. Confirm the CLI entry
    point surfaces both correctly too, including together in one file."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n1. one\n3. three\n\n| A | B |\n| --- | --- |\n| 1 | 2 | 3 |\n")

    exit_code = main([str(doc)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert lines == [
        f"{doc}:4: MDT02 ordered list item is numbered 3; expected 2 to continue the sequence",
        f"{doc}:8: MDT03 table row has 3 column(s); expected 2 to match the header",
    ]


def test_mdf01_mdf02_mdf03_violations_are_reported_through_the_cli(tmp_path, capsys):
    """The fence rules (MDF01-03) were only ever exercised via their own
    rule-level unit tests. Confirm the CLI entry point surfaces all three
    correctly too, including together in one file."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n```\ncode\n```\n\n~~~text\nmore\n")

    exit_code = main([str(doc)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert exit_code == 1
    assert lines == [
        f"{doc}:3: MDF01 fenced code block does not declare a language",
        f"{doc}:7: MDF02 fenced code block is never closed",
        f"{doc}:7: MDF03 fence marker '~' is inconsistent; file uses '`'",
    ]


def test_fix_rewrites_inconsistent_fence_markers_through_the_cli(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n```text\none\n```\n\n~~~text\ntwo\n~~~\n")

    exit_code = main(["--fix", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert doc.read_text() == "# Title\n\n```text\none\n```\n\n```text\ntwo\n```\n"


def test_fix_skips_an_unsafe_fence_conversion_and_still_reports_it(tmp_path, capsys):
    """Converting the ~~~ block would let its inner ``` line close it early, so
    the CLI must leave the file alone and keep reporting MDF03."""
    doc = tmp_path / "doc.md"
    original = "# Title\n\n```text\none\n```\n\n~~~markdown\n```\ninner\n```\n~~~\n"
    doc.write_text(original)

    exit_code = main(["--fix", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == f"{doc}:7: MDF03 fence marker '~' is inconsistent; file uses '`'\n"
    assert doc.read_text() == original


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


def test_format_json_escapes_non_ascii_filenames_instead_of_emitting_utf8(tmp_path, capsys):
    doc = tmp_path / "café.md"
    doc.write_text("Not a heading\n")

    exit_code = main(["--format", "json", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 1
    # json.dumps defaults to ensure_ascii=True, so the raw stdout bytes never
    # contain the literal "é" -- it's escaped as é. json.loads still
    # decodes it back to the original string, so round-tripping is unaffected;
    # this only locks in the on-the-wire representation for JSON consumers
    # that scan stdout as text before parsing it.
    assert "café" not in captured.out
    assert "caf\\u00e9.md" in captured.out
    payload = json.loads(captured.out)
    assert payload["violations"][0]["file"] == str(doc)


def test_ignore_skips_matching_files(tmp_path, capsys):
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Not a heading\n")

    exit_code = main(["--ignore", "dirty.md", str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_ignore_skips_nonexistent_file_without_a_read_error(tmp_path, capsys):
    missing = tmp_path / "missing.md"

    # --ignore filtering happens before the file is opened, so a pattern
    # matching a path that was never created (e.g. a generated file excluded
    # from linting) must not surface as a read error.
    exit_code = main(["--ignore", "missing.md", str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


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


def test_ignore_glob_pattern_matches_absolute_path_in_subdirectory(tmp_path, capsys):
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    dirty = vendor / "dirty.md"
    dirty.write_text("Not a heading\n")

    # The file argument is absolute (as it would be from shell glob
    # expansion), while the ignore pattern is a relative "dir/pattern"
    # pair. Matching must compare from the right, not by literal string
    # equality, or absolute-path invocations would bypass --ignore.
    exit_code = main(["--ignore", "vendor/*", str(dirty)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_ignore_recursive_glob_does_not_match_across_multiple_directories(
    tmp_path, capsys, monkeypatch
):
    nested = tmp_path / "docs" / "sub" / "deep"
    nested.mkdir(parents=True)
    dirty = nested / "dirty.md"
    dirty.write_text("Not a heading\n")
    monkeypatch.chdir(tmp_path)

    # PurePath.match treats "**" as a literal single path segment, not a
    # recursive-descent wildcard: one "**" only ever stands in for exactly
    # one directory level, unlike shell or gitignore "**" semantics. So a
    # two-level-deep file slips past a pattern written expecting arbitrary
    # depth. This locks in that (surprising) current behavior so a match
    # implementation swap doesn't silently start ignoring files it shouldn't.
    exit_code = main(["--ignore", "docs/**/*.md", "docs/sub/deep/dirty.md"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "docs/sub/deep/dirty.md" in captured.out


def test_ignore_bare_double_star_matches_every_file_regardless_of_depth(tmp_path, capsys):
    shallow = tmp_path / "doc.md"
    shallow.write_text("Not a heading\n")
    nested = tmp_path / "docs" / "sub"
    nested.mkdir(parents=True)
    deep = nested / "dirty.md"
    deep.write_text("Not a heading\n")

    # Unlike "docs/**/*.md" (see the test above), a *bare* "**" pattern has
    # no literal segments of its own to anchor against, so PurePath.match
    # treats it as matching any path regardless of depth -- effectively
    # "ignore everything". This is the opposite surprise from the one above
    # and worth locking in separately: both files are skipped, so linting
    # finds nothing and exits 0.
    exit_code = main(["--ignore", "**", str(shallow), str(deep)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_ignore_with_empty_pattern_exits_two_instead_of_crashing(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")

    # Path.match("") raises ValueError; this must surface as a clean CLI
    # error, not an unhandled traceback.
    exit_code = main(["--ignore", "", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "invalid --ignore pattern" in captured.err
    assert captured.out == ""


def test_ignore_pattern_of_a_single_dot_exits_two_instead_of_crashing(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")

    # Path.match(".") raises the same "empty pattern" ValueError as "": a
    # user reaching for "." to mean "the current directory" must get a clean
    # CLI error, not an unhandled traceback.
    exit_code = main(["--ignore", ".", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "invalid --ignore pattern" in captured.err
    assert captured.out == ""


def test_ignore_extension_glob_skips_every_matching_file(tmp_path, capsys):
    first = tmp_path / "a.md"
    first.write_text("Not a heading\n")
    second = tmp_path / "b.md"
    second.write_text("Not a heading\n")

    # A bare "*.md" pattern is a legitimate glob (e.g. to silence a run over
    # a directory that's entirely generated content); it should zero out the
    # whole file list rather than being treated as too broad to match.
    exit_code = main(["--ignore", "*.md", str(first), str(second)])

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


def test_config_enabled_list_with_duplicate_rule_id_runs_that_rule_once(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n# Title\n### Too deep\n")
    config = tmp_path / ".mdlintrc"
    # "enabled" going through a set() internally means a repeated id must not
    # produce duplicate violations for the same line.
    config.write_text(json.dumps({"enabled": ["MDS02", "MDS02"]}))

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


def test_config_with_empty_enabled_list_runs_no_rules(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": []}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


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


def test_explicit_config_flag_overrides_a_default_mdlintrc_in_cwd(tmp_path, capsys, monkeypatch):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n# Title\n### Too deep\n")
    (tmp_path / ".mdlintrc").write_text(json.dumps({"enabled": ["MDS01"]}))
    other_config = tmp_path / "other.mdlintrc"
    other_config.write_text(json.dumps({"enabled": ["MDS02"]}))
    monkeypatch.chdir(tmp_path)

    # A default .mdlintrc sits right next to the explicit --config target, so
    # this only proves the explicit flag wins if it's the *other* file's
    # rule set that actually shows up in the output.
    exit_code = main(["--config", str(other_config), "doc.md"])

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


def test_config_with_multiple_unknown_rule_ids_lists_each_in_order(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01", "MDS98", "MDS99"]}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "MDS98, MDS99" in captured.err


def test_config_with_duplicate_unknown_rule_id_lists_it_once_per_occurrence(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS99", "MDS99"]}))

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "MDS99, MDS99" in captured.err


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


def test_invalid_config_error_takes_priority_over_invalid_ignore_pattern(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text("{not json")

    # Rules are resolved (and the config parsed) before --ignore patterns
    # are validated, so a broken config must be reported even when an
    # --ignore pattern is also malformed, not the other way around.
    exit_code = main(["--config", str(config), "--ignore", "", str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err
    assert "invalid --ignore pattern" not in captured.err


def test_empty_config_file_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text("")

    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(config) in captured.err


def test_no_files_argument_exits_two_via_argparse(capsys):
    # `files` is a required nargs="+" positional, so calling mdlint with none
    # never reaches mdlint's own logic at all; this locks in that argparse's
    # own usage error still surfaces as the same exit code 2 contract as
    # every other invalid-invocation case (bad --format, bad --config, etc.).
    with pytest.raises(SystemExit) as excinfo:
        main([])

    captured = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "the following arguments are required: files" in captured.err


def test_invalid_format_choice_exits_two(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")

    # argparse's `choices=` rejects an unknown --format value before mdlint's
    # own logic ever runs; this locks in that it surfaces as the same clean
    # exit code 2 (via SystemExit) rather than some other status.
    with pytest.raises(SystemExit) as excinfo:
        main(["--format", "xml", str(doc)])

    captured = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "invalid choice" in captured.err


def test_format_json_reports_invalid_config_as_structured_data_on_stdout(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text("{not json")

    # A JSON-format caller may not read stderr at all, so a config error
    # must still surface as parseable JSON on stdout, not silence there.
    exit_code = main(["--format", "json", "--config", str(config), str(doc)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert str(config) in captured.err
    assert payload["violations"] == []
    assert payload["errors"] == []
    assert str(config) in payload["error"]


def test_format_json_reports_invalid_ignore_pattern_as_structured_data_on_stdout(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")

    exit_code = main(["--format", "json", "--ignore", "", str(doc)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert payload["violations"] == []
    assert payload["errors"] == []
    assert "invalid --ignore pattern" in payload["error"]


def test_format_text_config_error_does_not_print_to_stdout(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n")
    config = tmp_path / ".mdlintrc"
    config.write_text("{not json")

    # Default (text) format must be unaffected: the structured payload is a
    # JSON-format-only addition, not a change to plain-text behavior.
    exit_code = main(["--config", str(config), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
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


def test_fix_with_empty_enabled_list_leaves_the_file_untouched(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading\n\n- one\n* two  \n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": []}))

    # With every rule disabled, --fix has no fixer to run and lint_lines has
    # nothing to check: the file must come out byte-for-byte identical, not
    # just "no violations reported".
    exit_code = main(["--fix", "--config", str(config), str(doc)])

    assert exit_code == 0
    assert doc.read_text() == "Not a heading\n\n- one\n* two  \n"


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


def test_fix_with_the_same_file_passed_twice_is_idempotent(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\n- one\n* two\n")

    # The same path appearing twice in argv (e.g. from overlapping shell
    # globs) must not corrupt the file: the second pass reads the
    # already-fixed content back off disk, finds nothing left to fix, and
    # reports clean rather than re-applying (or mangling) the autofix.
    exit_code = main(["--fix", str(doc), str(doc)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert doc.read_text() == "# Title\n\n- one\n- two\n"


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


@pytest.mark.skipif(
    shutil.which("mdlint") is None,
    reason="installed mdlint console script not found on PATH",
)
def test_installed_console_script_combines_fix_config_format_and_ignore(tmp_path):
    """Exercise the packaged ``mdlint`` entry point as a real subprocess.

    Every other test drives ``main()`` in-process, which never runs through
    the ``[project.scripts]`` console_scripts wrapper that actually turns
    ``main``'s return value into a process exit code. This is the one test
    that invokes the installed binary directly, so a packaging regression
    (e.g. a broken entry point) fails here even though every in-process test
    still passes.
    """
    kept = tmp_path / "doc.md"
    kept.write_text("Not a heading\n\nSome text.   \n\n\n1. one\n3. two\n")
    ignored = tmp_path / "vendor.md"
    ignored.write_text("Not a heading\n\n1. one\n3. two\n")
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": ["MDS01", "MDW01", "MDT02"]}))

    result = subprocess.run(
        [
            "mdlint",
            "--fix",
            "--format",
            "json",
            "--config",
            str(config),
            "--ignore",
            "vendor.md",
            str(kept),
            str(ignored),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["errors"] == []
    # --fix removed the trailing space (MDW01) and renumbered the ordered
    # list (MDT02), but MDS01 (missing H1) has no safe autofix and is left
    # both on disk and in the reported violations.
    assert kept.read_text() == "Not a heading\n\nSome text.\n\n\n1. one\n2. two\n"
    assert [v["rule_id"] for v in payload["violations"]] == ["MDS01"]
    # --ignore excluded vendor.md entirely: untouched on disk, no violations.
    assert ignored.read_text() == "Not a heading\n\n1. one\n3. two\n"


def test_fence_marker_consistency_is_scoped_to_each_file(tmp_path, capsys):
    """MDF03 says "consistent within a file": one file's marker must not
    become the expected marker for the next file on the command line."""
    backticks = tmp_path / "backticks.md"
    tildes = tmp_path / "tildes.md"
    backticks.write_text("# Title\n\n```text\none\n```\n")
    tildes.write_text("# Title\n\n~~~text\ntwo\n~~~\n")

    exit_code = main([str(backticks), str(tildes)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_empty_file_is_clean_in_text_and_json_and_untouched_by_fix(tmp_path, capsys):
    """A zero-byte file has no "first line" for MDS01 to flag and nothing for
    MDW04's trailing-newline check to fix, so it must round-trip as clean
    through every mode without crashing or triggering a spurious rewrite."""
    doc = tmp_path / "empty.md"
    doc.write_text("")

    exit_code = main([str(doc)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""

    exit_code = main(["--format", "json", str(doc)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {"violations": [], "errors": []}

    original_mtime = doc.stat().st_mtime_ns
    exit_code = main(["--fix", str(doc)])
    assert exit_code == 0
    assert doc.read_text() == ""
    assert doc.stat().st_mtime_ns == original_mtime


def test_fix_makes_each_file_consistent_with_its_own_first_fence(tmp_path, capsys):
    backticks = tmp_path / "backticks.md"
    tildes = tmp_path / "tildes.md"
    backticks.write_text("# Title\n\n```text\none\n```\n\n~~~text\ntwo\n~~~\n")
    tildes.write_text("# Title\n\n~~~text\none\n~~~\n\n```text\ntwo\n```\n")

    exit_code = main(["--fix", str(backticks), str(tildes)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert backticks.read_text() == "# Title\n\n```text\none\n```\n\n```text\ntwo\n```\n"
    assert tildes.read_text() == "# Title\n\n~~~text\none\n~~~\n\n~~~text\ntwo\n~~~\n"


def test_fix_skips_a_fenceless_file_between_two_files_needing_fence_fixes(tmp_path, capsys):
    """A plain file with no fences at all, sandwiched between two files that
    do need MDF03 fixes, must not disrupt either neighbor's fix or scoping."""
    first = tmp_path / "first.md"
    middle = tmp_path / "middle.md"
    last = tmp_path / "last.md"
    first.write_text("# Title\n\n```text\none\n```\n\n~~~text\ntwo\n~~~\n")
    middle.write_text("# Title\n\nNo fences here, just prose.\n")
    last.write_text("# Title\n\n~~~text\none\n~~~\n\n```text\ntwo\n```\n")

    exit_code = main(["--fix", str(first), str(middle), str(last)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert first.read_text() == "# Title\n\n```text\none\n```\n\n```text\ntwo\n```\n"
    assert middle.read_text() == "# Title\n\nNo fences here, just prose.\n"
    assert last.read_text() == "# Title\n\n~~~text\none\n~~~\n\n~~~text\ntwo\n~~~\n"


def test_ignored_nonexistent_file_is_skipped_without_error(tmp_path, capsys):
    missing = tmp_path / "vendor" / "gone.md"

    exit_code = main([str(missing), "--ignore", "vendor/*", "--config", str(tmp_path / "rc")])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_config_with_null_enabled_runs_every_rule(tmp_path, capsys):
    config = tmp_path / ".mdlintrc"
    config.write_text(json.dumps({"enabled": None}))
    doc = tmp_path / "doc.md"
    doc.write_text("## Title\n")

    exit_code = main([str(doc), "--config", str(config)])

    assert exit_code == 1
    assert "MDS01" in capsys.readouterr().out
