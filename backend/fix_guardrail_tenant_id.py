"""
One-time fix script.

GuardrailFallbackService.__init__ now requires tenant_id as a
required keyword-only argument. A batch of tests across four files
were written before that requirement existed and only pass db=...,
causing:

    TypeError: GuardrailFallbackService.__init__() missing 1
    required keyword-only argument: 'tenant_id'

This script finds every GuardrailFallbackService(...) constructor
call in the target files and inserts tenant_id="tenant-1" if it is
not already present. It does NOT touch any other code.

Usage (run from the backend/ project root):

    python fix_guardrail_tenant_id.py

It edits files in place. Run `git diff` afterward to review the
changes before committing.
"""

from __future__ import annotations

import re
from pathlib import Path

TARGET_FILES = [
    "tests/test_guardrail_fallback_service.py",
    "tests/test_communication_configuration.py",
    "tests/test_communication_configuration_cache_consistency.py",
    "tests/test_message_template_engine.py",
    "tests/test_status_template_selection.py",
    "tests/test_communication_delivery_policy.py",
]

# Matches GuardrailFallbackService( ... ) across multiple lines,
# lazily, so it stops at the first closing paren that ends the call.
CALL_PATTERN = re.compile(
    r"GuardrailFallbackService\(\s*(.*?)\s*\)",
    re.DOTALL,
)


def fix_call(match: re.Match) -> str:
    args = match.group(1)

    if "tenant_id" in args:
        # Already has it — leave untouched.
        return match.group(0)

    args = args.rstrip()

    if args.endswith(","):
        new_args = f'{args}\n        tenant_id="tenant-1",'
    elif args:
        new_args = f'{args}, tenant_id="tenant-1"'
    else:
        new_args = 'tenant_id="tenant-1"'

    return f"GuardrailFallbackService({new_args})"


def main() -> None:
    root = Path(".")
    total_changes = 0

    for rel_path in TARGET_FILES:
        path = root / rel_path

        if not path.exists():
            print(f"SKIP (not found): {rel_path}")
            continue

        original = path.read_text(encoding="utf-8")
        updated, count = CALL_PATTERN.subn(fix_call, original)

        if count == 0:
            print(f"No GuardrailFallbackService(...) calls found in {rel_path}")
            continue

        path.write_text(updated, encoding="utf-8")
        print(f"Updated {count} call(s) in {rel_path}")
        total_changes += count

    print(f"\nDone. {total_changes} call(s) updated across "
          f"{len(TARGET_FILES)} target file(s).")
    print("Review with: git diff")


if __name__ == "__main__":
    main()