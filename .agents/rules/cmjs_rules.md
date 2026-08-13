# CMJS Editorial & Reference Format Rules

Use these rules whenever formatting manuscripts or checking references for Chiang Mai Journal of Science (CMJS).

## Reference Formatting Rules (Vancouver Style)
1. Font: Calibri 10pt, Justified alignment.
2. Entry Prefix: `[n]` followed by a tab.
3. Author Names: `Surname I.` (Always add trailing period after initials).
4. Author Truncation: If authors > 6, list first 6 authors followed by `et al.`.
5. Journal Names: Must be **italicized full names** (never abbreviated).
6. Volume: Must be **bold**.
7. Issue Number: Enclosed in parentheses after volume, e.g., `51(2): 100-105.`.
8. DOI Format: `DOI 10.xxxx/xxxx` (remove `https://doi.org/` prefix).

## Verification Pipeline (3-Tier Cascade)
1. Tier 1: Look up DOI via CrossRef API.
2. Tier 2: If no DOI or DOI mismatch, search article title via CrossRef Bibliographic & Semantic Scholar API.
3. Tier 3: If unverified, flag as `❌ Cannot verify — Missing, Incorrect, or Potentially AI-Generated`.

## Automatic Corrections & Quality Checks
- Auto-add dots after author initials (e.g. `Sarkar A` -> `Sarkar A.`).
- Auto-convert APA semicolon author lists (`Li, J.; Xu, P.;`) to Vancouver comma lists (`Li J., Xu P.,`).
- Flag duplicate references (similarity >= 85%).
- Flag author surname mismatches and Pinyin name order issues.
