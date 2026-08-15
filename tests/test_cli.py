"""Tests for the mdlint command-line entry point."""

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
