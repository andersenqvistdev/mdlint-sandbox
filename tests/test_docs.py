"""Guards README.md and docs/rules.md against drifting from the rule registry.

G9 requires the rule reference to document every implemented rule with a
passing and a failing example. This is easy to violate silently: a new rule
module registers itself (see mdlint.rules.__init__) without anything forcing
a matching docs update. These tests fail CI the moment that happens.
"""

import re
from pathlib import Path

from mdlint.rules import all_rules

REPO_ROOT = Path(__file__).resolve().parent.parent
RULE_HEADING_RE = re.compile(r"^### (MD[A-Z]\d{2}) ", re.MULTILINE)


def _rules_doc_text() -> str:
    return (REPO_ROOT / "docs" / "rules.md").read_text()


def test_every_registered_rule_has_a_doc_entry():
    documented = set(RULE_HEADING_RE.findall(_rules_doc_text()))
    registered = {rule.id for rule in all_rules()}

    assert registered <= documented, (
        f"rules missing from docs/rules.md: {sorted(registered - documented)}"
    )


def test_docs_do_not_reference_unregistered_rules():
    documented = set(RULE_HEADING_RE.findall(_rules_doc_text()))
    registered = {rule.id for rule in all_rules()}

    assert documented <= registered, (
        f"docs/rules.md documents rule ids that are not registered: "
        f"{sorted(documented - registered)}"
    )


def test_every_doc_entry_has_a_passing_and_failing_example():
    text = _rules_doc_text()
    sections = re.split(r"^### MD[A-Z]\d{2} ", text, flags=re.MULTILINE)[1:]

    for section in sections:
        heading = section.splitlines()[0]
        passing_idx = section.find("Passing")
        failing_idx = section.find("Failing")
        assert passing_idx != -1, f"section '{heading}' missing a Passing example"
        assert failing_idx != -1, f"section '{heading}' missing a Failing example"
        assert passing_idx < failing_idx, (
            f"section '{heading}' does not present Passing before Failing"
        )
        # Each label must be followed by its own non-empty fenced code block
        # before the next label (or the end of the section) — not just the
        # bare word somewhere in the text.
        passing_block = section[passing_idx:failing_idx]
        failing_block = section[failing_idx:]
        for label, block in (("Passing", passing_block), ("Failing", failing_block)):
            fence = re.search(r"```[a-z]*\n(.*?)\n```", block, re.DOTALL)
            assert fence, f"section '{heading}' has no fenced code block for '{label}'"
            assert fence.group(1).strip(), (
                f"section '{heading}' has an empty fenced code block for '{label}'"
            )


def test_readme_documents_install_and_usage():
    readme = (REPO_ROOT / "README.md").read_text()

    assert re.search(r"^## Install$", readme, re.MULTILINE)
    assert re.search(r"^## Usage$", readme, re.MULTILINE)
    assert "pip install" in readme
    assert "mdlint" in readme


def test_readme_rule_count_matches_registry():
    readme = (REPO_ROOT / "README.md").read_text()
    count = len(all_rules())

    assert f"{count} rules" in readme, (
        f"README claims a stale rule count; registry has {count} rules"
    )
