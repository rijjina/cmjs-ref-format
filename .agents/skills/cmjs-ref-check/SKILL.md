---
name: cmjs-ref-check
description: >-
  Use this skill when the user asks to check, verify, or fix references/bibliography
  in a CMJS journal article (.docx). Validates citation format, cross-matches in-text
  citations with reference list, verifies references via CrossRef API, and checks
  formatting compliance with CMJS Vancouver-style guidelines.
---

# cmjs-ref-check Skill

This skill guides you through checking and fixing references in CMJS journal articles (.docx).

## Instructions

1. **Get File Path:** Ask the user for the absolute path to the `.docx` file they want to check.
2. **Parse References:** Run `python scripts/parse_references.py <input.docx> --output parsed_refs.json` to extract references and in-text citations.
3. **Verify References:** Run `python scripts/verify_references.py parsed_refs.json --output verification.json` to cross-check extracted references against the CrossRef API (and other academic APIs).
4. **Fix References:** Run `python scripts/fix_references.py <input.docx> parsed_refs.json verification.json <output_dir>` to auto-fix correctable issues, generate a corrected DOCX, and produce a Markdown report.
5. **Present Report:** Present the generated Markdown report (`<output_dir>/<original_name>_ref_report.md`) to the user.
6. **Manual Review:** Ask the user to review any issues marked for manual intervention in the report (e.g., references that couldn't be automatically fixed or weren't found in academic databases).

## Reference Material
For manual verification or answering user questions, refer to the CMJS reference format rules at `references/cmjs_ref_format_rules.md`.
