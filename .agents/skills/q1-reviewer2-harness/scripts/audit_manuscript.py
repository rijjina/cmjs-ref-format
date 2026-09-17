#!/usr/bin/env python3
"""
audit_manuscript.py — Deep Forensic Manuscript & Reference Audit Tool
Part of the Antigravity 'q1-reviewer2-harness' skill.

Features:
1. Ingests .docx or .txt manuscripts.
2. Performs bidirectional citation cross-matching (in-text vs. reference list).
3. Verifies citation sequence (numerical order on first appearance).
4. Concurrently verifies all references via Crossref API and doi.org resolution.
5. Flags AI-generated/hallucinated DOIs, corrupted suffixes, and mismatched paper metadata.
6. Evaluates formatting compliance against target journal rules (default: CMJS Vancouver style).
7. Outputs structured JSON and a Markdown audit summary table.
"""

import os
import sys
import re
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import concurrent.futures

try:
    import docx
except ImportError:
    docx = None

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    paragraphs = []
    
    if ext == ".docx":
        if docx is None:
            raise RuntimeError("python-docx is required to read .docx files. Install via 'pip install python-docx'.")
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            paragraphs = [line.strip() for line in f if line.strip()]
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .docx, .txt, .md")
    
    return paragraphs

def parse_citations_and_references(paragraphs):
    ref_start_idx = -1
    for i, p in enumerate(paragraphs):
        if re.match(r'^(REFERENCES|BIBLIOGRAPHY|LITERATURE CITED)\b', p.strip(), re.IGNORECASE):
            ref_start_idx = i
            break
            
    if ref_start_idx == -1:
        for i, p in enumerate(paragraphs):
            if re.match(r'^\[1\]\s+[A-Z]', p.strip()):
                ref_start_idx = i
                break

    if ref_start_idx == -1:
        raise ValueError("Could not locate REFERENCES section in manuscript.")

    body_paras = paragraphs[:ref_start_idx]
    ref_paras = paragraphs[ref_start_idx + 1:]

    in_text_citations = []
    citation_occurrences = []

    for p_idx, p in enumerate(body_paras):
        matches = re.finditer(r'\[([0-9\s,\-–—]+)\]', p)
        for m in matches:
            content = m.group(1).strip()
            parts = re.split(r'[,;]', content)
            nums = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if '-' in part or '–' in part or '—' in part:
                    sub = re.split(r'[\-–—]', part)
                    if len(sub) == 2 and sub[0].strip().isdigit() and sub[1].strip().isdigit():
                        nums.extend(range(int(sub[0].strip()), int(sub[1].strip()) + 1))
                elif part.isdigit():
                    nums.append(int(part))
            if nums:
                citation_occurrences.append((m.group(0), nums, p_idx, p[:80]))
                in_text_citations.extend(nums)

    unique_in_text = sorted(list(set(in_text_citations)))

    ref_dict = {}
    current_num = None
    current_text = []

    for p in ref_paras:
        m = re.match(r'^\[(\d+)\]\s*(.*)', p, re.DOTALL)
        if m:
            if current_num is not None:
                ref_dict[current_num] = " ".join(current_text).strip()
            current_num = int(m.group(1))
            current_text = [m.group(2).strip()]
        else:
            if current_num is not None:
                current_text.append(p.strip())
    if current_num is not None:
        ref_dict[current_num] = " ".join(current_text).strip()

    curr_max = 0
    out_of_order = []
    seen = set()
    for raw_str, nums, p_idx, snippet in citation_occurrences:
        for n in nums:
            if n not in seen:
                seen.add(n)
                if n != curr_max + 1:
                    out_of_order.append({"citation": n, "expected": curr_max + 1, "raw": raw_str, "context": snippet})
                curr_max = max(curr_max, n)

    ref_keys = sorted(list(ref_dict.keys()))
    missing_in_refs = sorted(list(set(unique_in_text) - set(ref_keys)))
    missing_in_text = sorted(list(set(ref_keys) - set(unique_in_text)))

    return {
        "body_paragraphs": len(body_paras),
        "total_citations_found": len(citation_occurrences),
        "unique_in_text": unique_in_text,
        "ref_keys": ref_keys,
        "missing_in_refs": missing_in_refs,
        "missing_in_text": missing_in_text,
        "out_of_order": out_of_order,
        "references": ref_dict
    }

def verify_single_doi(num, text, user_email="reviewer2@journal-review.org"):
    doi_match = re.search(r'DOI\s*[:\s]*\s*(10\.\d{4,9}/[^\s,;]+)', text, re.IGNORECASE)
    doi = doi_match.group(1).rstrip('.') if doi_match else None

    item_res = {
        "ref_num": num,
        "raw_text": text,
        "doi": doi,
        "status": "UNVERIFIED",
        "doi_resolves": False,
        "crossref_match": False,
        "title_similarity": 0.0,
        "crossref_title": None,
        "crossref_authors": None,
        "crossref_journal": None,
        "crossref_year": None,
        "flags": []
    }

    if not doi:
        if re.search(r'\b(Press|Publishers|McGraw|Springer|Wiley|Book|Edition|Edn)\b', text, re.IGNORECASE):
            item_res["status"] = "BOOK_OR_REPORT"
        else:
            item_res["status"] = "NO_DOI"
            item_res["flags"].append("Missing DOI for journal reference")
        return item_res

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    headers = {
        "User-Agent": f"AntigravityQ1Reviewer/2.0 (mailto:{user_email})",
        "Accept": "application/json"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                item_res["doi_resolves"] = True
                data = json.loads(response.read().decode('utf-8')).get("message", {})
                item_res["crossref_match"] = True
                
                title = data.get("title", [""])[0] if data.get("title") else ""
                journal = data.get("container-title", [""])[0] if data.get("container-title") else ""
                
                authors = []
                for a in data.get("author", []):
                    authors.append(f"{a.get('family', '')} {a.get('given', '')}".strip())
                author_str = "; ".join(authors)

                published = data.get("published-print", data.get("published-online", data.get("created", {})))
                year = published.get("date-parts", [[None]])[0][0] if published.get("date-parts") else None

                item_res["crossref_title"] = title
                item_res["crossref_journal"] = journal
                item_res["crossref_authors"] = author_str
                item_res["crossref_year"] = year

                t_words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', title)]
                raw_lower = text.lower()
                matched = [w for w in t_words if w in raw_lower]
                sim = len(matched) / len(t_words) if t_words else 0.0
                item_res["title_similarity"] = round(sim, 2)

                if sim < 0.4:
                    item_res["status"] = "MISMATCHED_DOI"
                    item_res["flags"].append(f"DOI points to different paper: '{title}' in {journal}")
                else:
                    item_res["status"] = "VERIFIED_OK"
                    
    except urllib.error.HTTPError as e:
        if e.code == 404:
            item_res["status"] = "INVALID_DOI_404"
            item_res["flags"].append("DOI not found in Crossref (404) — probable AI hallucination or typo")
        elif e.code in [403, 429]:
            item_res["status"] = "PROTECTED_OR_RATELIMIT"
            item_res["flags"].append(f"HTTP {e.code} during lookup (publisher bot-protection)")
        else:
            item_res["status"] = f"HTTP_{e.code}"
            item_res["flags"].append(f"Lookup error: HTTP {e.code}")
    except Exception as e:
        item_res["status"] = "LOOKUP_ERROR"
        item_res["flags"].append(str(e))

    return item_res

def check_cmjs_formatting(ref_dict):
    formatting_issues = []
    for num, text in ref_dict.items():
        has_title_pattern = re.search(r'^[A-Z][a-zA-Z\s\.,\-\'\’]+?,\s+([A-Z][^,\.;:]+[\.\?])\s+[A-Z]', text)
        if has_title_pattern:
            potential_title = has_title_pattern.group(1)
            if len(potential_title.split()) >= 3 and not re.search(r'\b(Edn|Vol|Press|University)\b', potential_title):
                formatting_issues.append({
                    "ref_num": num,
                    "issue": "Article title included (CMJS style requires omitting article titles for journals)",
                    "snippet": potential_title[:50]
                })

        if "https://doi.org/" in text or "http://dx.doi.org/" in text:
            formatting_issues.append({
                "ref_num": num,
                "issue": "DOI prefix includes URL (should be formatted as 'DOI 10.xxxx/yyyy')",
                "snippet": text[-40:]
            })
            
    return formatting_issues

def run_audit(input_file, output_dir=None, max_workers=10):
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_file))
    os.makedirs(output_dir, exist_ok=True)

    print(f"[*] Reading manuscript: {input_file}")
    paras = extract_text_from_file(input_file)
    print(f"[*] Total paragraphs read: {len(paras)}")

    print("[*] Analyzing citations and reference structure...")
    parsed = parse_citations_and_references(paras)
    refs = parsed["references"]
    print(f"[*] Found {len(refs)} references in bibliography.")
    print(f"[*] Found {len(parsed['unique_in_text'])} unique cited reference numbers in text.")

    if parsed["missing_in_refs"]:
        print(f"[!] Warning: Citations in text missing from bibliography: {parsed['missing_in_refs']}")
    if parsed["missing_in_text"]:
        print(f"[!] Warning: Bibliography items never cited in text: {parsed['missing_in_text']}")
    if parsed["out_of_order"]:
        print(f"[!] Warning: {len(parsed['out_of_order'])} citations appeared out of numerical sequence.")

    print(f"[*] Concurrently verifying {len(refs)} references against Crossref API...")
    verified_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_num = {executor.submit(verify_single_doi, num, text): num for num, text in refs.items()}
        for future in concurrent.futures.as_completed(future_to_num):
            res = future.result()
            verified_results[res["ref_num"]] = res

    sorted_verified = [verified_results[k] for k in sorted(verified_results.keys())]

    print("[*] Auditing journal formatting compliance (CMJS style)...")
    formatting_issues = check_cmjs_formatting(refs)

    report_path = os.path.join(output_dir, "manuscript_audit_summary.md")
    json_path = os.path.join(output_dir, "manuscript_audit_data.json")

    invalid_or_mismatched = [r for r in sorted_verified if r["status"] in ["INVALID_DOI_404", "MISMATCHED_DOI"]]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Manuscript Forensic Reference & Citation Audit\n\n")
        f.write(f"**Input File:** `{os.path.basename(input_file)}`  \n")
        f.write(f"**Total References:** {len(refs)}  \n")
        f.write(f"**Total In-Text Citations:** {parsed['total_citations_found']}  \n")
        f.write(f"**Citation Integrity:** {'PASS (100% matched)' if not parsed['missing_in_refs'] and not parsed['missing_in_text'] else 'FAIL'}  \n")
        f.write(f"**Corrupted / Hallucinated DOIs Detected:** {len(invalid_or_mismatched)} / {len(refs)}  \n\n")

        if parsed["missing_in_refs"] or parsed["missing_in_text"] or parsed["out_of_order"]:
            f.write("## Citation Consistency Flags\n")
            if parsed["missing_in_refs"]:
                f.write(f"- **Cited in text but missing from list:** {parsed['missing_in_refs']}\n")
            if parsed["missing_in_text"]:
                f.write(f"- **Listed in references but never cited in text:** {parsed['missing_in_text']}\n")
            if parsed["out_of_order"]:
                f.write(f"- **Out of numerical order on first appearance:** {len(parsed['out_of_order'])} instances\n")
            f.write("\n")

        f.write("## Flagged / Suspicious References Table\n\n")
        f.write("| Ref # | Status | Provided DOI | Crossref Result / Diagnosis |\n")
        f.write("|---|---|---|---|\n")
        for r in sorted_verified:
            if r["flags"] or r["status"] != "VERIFIED_OK":
                flag_desc = "; ".join(r["flags"]) if r["flags"] else r["status"]
                f.write(f"| **[{r['ref_num']}]** | `{r['status']}` | `{r['doi'] or 'None'}` | {flag_desc} |\n")
        f.write("\n")

        if formatting_issues:
            f.write("## Journal Style Compliance (CMJS)\n\n")
            f.write(f"Detected **{len(formatting_issues)}** formatting warnings:\n")
            for iss in formatting_issues[:15]:
                f.write(f"- Ref `[{iss['ref_num']}]`: {iss['issue']} (near: `{iss['snippet']}`)\n")
            if len(formatting_issues) > 15:
                f.write(f"- *...and {len(formatting_issues) - 15} more references.*\n")
            f.write("\n")

    audit_data = {
        "file": input_file,
        "parsed": parsed,
        "verified": sorted_verified,
        "formatting_issues": formatting_issues
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Audit complete!")
    print(f"[+] Markdown report saved to: {report_path}")
    print(f"[+] Detailed JSON saved to: {json_path}")
    return audit_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit manuscript references and citations for peer review.")
    parser.add_argument("input_file", help="Path to .docx or .txt manuscript")
    parser.add_argument("--output_dir", default=None, help="Directory to save audit reports")
    args = parser.parse_args()

    run_audit(args.input_file, args.output_dir)
