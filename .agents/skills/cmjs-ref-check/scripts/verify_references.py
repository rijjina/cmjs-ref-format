import sys
import argparse
import json
import requests
import time
import difflib
import re

JOURNAL_ABBREV_PATTERNS = [
    r'\bOpt\s+Mater\b', r'\bCeram\s+Int\b', r'\bJ\s+Mater\b', r'\bElectrochim\s+Acta\b',
    r'\bMater\s+Sci\b', r'\bJ\s+Alloys\s+Compd\b', r'\bJ\s+Mol\s+Liq\b', r'\bJ\s+Environ\s+Chem\s+Eng\b',
    r'\bSuperlattices\s+Microstruct\b', r'\bAppl\s+Surf\s+Sci\b', r'\bNanotechnol\s+Rev\b',
    r'\bPhysica\s+B\b', r'\bJ\s+Mater\s+Sci\s+Technol\b',
    r'\bFront\s+Microbiol\b', r'\bWorld\s+J\s+Microbiol\b', r'\bLWT\b',
    r'\bInt\s+J\b', r'\bEur\s+J\b', r'\bAnn\s+Agri\b', r'\bOrnam\s+Horti\b',
    r'\bHortScience\b', r'\bSci\s+Hortic\b', r'\bJ\s+Plant\s+Physiol\b',
]

HEADERS = {'User-Agent': 'CMJS-RefCheck-Bot/1.0 (mailto:admin@science.cmu.ac.th)'}


def check_journal_abbreviated(text: str) -> bool:
    if not text:
        return False
    for pat in JOURNAL_ABBREV_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    if re.search(r'\b[A-Z][a-z]{1,4}\.', text):
        return True
    return False


def extract_title_from_raw(raw_text: str) -> str:
    """
    Extract the article/book title from a CMJS Vancouver-style reference string.
    Supports both dot-initials ('Surname I.') and no-dot initials ('Surname I').
    """
    text = re.sub(r'^\[\d+\]\s*\t?\s*', '', raw_text.strip())

    # --- Case 1: et al. → title starts right after "et al.," ---
    m_etal = re.search(r'et\s+al\.(?:,|\s)', text, re.IGNORECASE)
    if m_etal:
        after = text[m_etal.end():].strip().lstrip(',')
        parts = re.split(r'\.\s+[A-Z]', after)
        if parts:
            return parts[0].strip()[:200]

    # --- Case 2: Author block pattern (with or without dots after initials) ---
    m_auth = re.match(
        r'^(?:[A-ZÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÇÑÃÕÂÊÎÔÛĂĄĆĘŁŃŚŹŻ][a-z\-]+\s+[A-Z]{1,3}(?:\.|\b)(?:,\s*|\s+and\s+|\.\s+))+(.*)',
        text
    )
    if m_auth:
        title_candidate = m_auth.group(1).strip()
        trimmed = re.split(r'\.\s+[A-Z][a-z]+(?:nal|ence|ogy|ics|iew|ism|ist|ure|tion)', title_candidate)
        if trimmed and len(trimmed[0]) > 10:
            return trimmed[0].strip()[:200]
        return title_candidate[:200]

    # --- Case 3: Fallback by period split ---
    parts = text.split('. ')
    if len(parts) > 1:
        return parts[1][:200]
    return text[:150]


def extract_author_surnames_from_text(raw_text: str) -> list:
    """Extract author surnames from CMJS-formatted reference text."""
    text = re.sub(r'^\[\d+\]\s*\t?\s*', '', raw_text.strip())
    # Stop searching if et al. is reached to avoid matching title/journal words
    et_al_match = re.search(r'et\s+al\.', text, re.IGNORECASE)
    search_text = text[:et_al_match.start()] if et_al_match else text[:300]

    surname_pattern = re.compile(
        r'([A-ZÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÇÑÃÕÂÊÎÔÛĂĄĆĘŁŃŚŹŻ][a-záéíóúàèìòùäëïöüçñãõâêîôûăąćęłńśźżó]+'
        r'(?:\s+[A-Z][a-z]+)*(?:\-[A-Z][a-záéíóúàèìòùäëïöüçñãõâêîôûăąćęłńśźż]+)*)'
        r'\s+[A-Z]{1,3}(?:\.[A-Z])?\.?'
    )
    return [m.group(1).lower() for m in surname_pattern.finditer(search_text)]


def format_authors_cmjs(api_authors: list) -> str:
    """Format CrossRef author list into CMJS Vancouver style."""
    formatted = []
    for a in api_authors:
        family = a.get('family', '')
        given = a.get('given', '')
        if not family:
            continue
        initials = ''
        if given:
            for part in re.split(r'[\s\-]+', given):
                part = part.strip('.')
                if part:
                    initials += part[0].upper() + '.'
        formatted.append(f"{family} {initials}".strip())

    if not formatted:
        return ''
    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    elif len(formatted) <= 6:
        return ', '.join(formatted[:-1]) + f" and {formatted[-1]}"
    else:
        return ', '.join(formatted[:6]) + ' et al.'


def compare_authors(ref_surnames: list, api_authors: list) -> dict:
    """Compare extracted surnames against CrossRef API author surnames."""
    api_surnames = [a.get('family', '').lower() for a in api_authors if a.get('family')]
    if not ref_surnames or not api_surnames:
        return {'has_mismatch': False, 'details': []}

    details = []
    has_mismatch = False
    compare_len = min(len(ref_surnames), len(api_surnames))
    for i in range(compare_len):
        ratio = difflib.SequenceMatcher(None, ref_surnames[i], api_surnames[i]).ratio()
        if ratio < 0.75:
            has_mismatch = True
            details.append({
                'position': i + 1,
                'in_text': ref_surnames[i],
                'in_crossref': api_surnames[i],
                'similarity': round(ratio, 2),
            })
    return {'has_mismatch': has_mismatch, 'details': details}


def lookup_by_doi(doi: str) -> dict:
    """Look up a reference by DOI via CrossRef API. Returns raw API message or None."""
    doi_clean = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi).strip().rstrip('.,;')
    try:
        resp = requests.get(
            f"https://api.crossref.org/works/{doi_clean}",
            headers=HEADERS, timeout=12
        )
        if resp.status_code == 200:
            return resp.json().get('message')
    except Exception as e:
        print(f"  DOI lookup error: {e}", file=sys.stderr)
    return None


def lookup_by_title(title: str) -> dict:
    """
    Search CrossRef by title. Returns best matching API message or None.
    Tries CrossRef first, then Semantic Scholar as fallback.
    """
    if not title or len(title) < 10:
        return None

    # --- CrossRef title search ---
    try:
        params = {'query.bibliographic': title[:200], 'rows': 3}
        resp = requests.get(
            'https://api.crossref.org/works',
            params=params, headers=HEADERS, timeout=12
        )
        if resp.status_code == 200:
            items = resp.json().get('message', {}).get('items', [])
            for item in items:
                api_title = item.get('title', [''])[0]
                ratio = difflib.SequenceMatcher(
                    None, title.lower()[:120], api_title.lower()[:120]
                ).ratio()
                if ratio >= 0.70:
                    item['_match_source'] = 'crossref_title'
                    item['_match_ratio'] = ratio
                    return item
    except Exception as e:
        print(f"  CrossRef title search error: {e}", file=sys.stderr)

    # --- Semantic Scholar fallback ---
    try:
        params = {'query': title[:150], 'limit': 3, 'fields': 'title,authors,year,externalIds'}
        resp = requests.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params=params, timeout=10
        )
        if resp.status_code == 200:
            items = resp.json().get('data', [])
            for item in items:
                api_title = item.get('title', '')
                ratio = difflib.SequenceMatcher(
                    None, title.lower()[:120], api_title.lower()[:120]
                ).ratio()
                if ratio >= 0.70:
                    # Convert S2 format to CrossRef-like for compatibility
                    s2_authors = [
                        {'family': a['name'].split()[-1], 'given': ' '.join(a['name'].split()[:-1])}
                        for a in item.get('authors', [])
                    ]
                    return {
                        'title': [api_title],
                        'author': s2_authors,
                        'container-title': [''],
                        'volume': '',
                        'issue': '',
                        'DOI': item.get('externalIds', {}).get('DOI', ''),
                        '_match_source': 'semantic_scholar',
                        '_match_ratio': ratio,
                    }
    except Exception as e:
        print(f"  Semantic Scholar search error: {e}", file=sys.stderr)

    return None


def verify_reference(ref: dict) -> dict:
    """
    Full verification pipeline:
    1. Try DOI lookup via CrossRef
    2. If no DOI or DOI title mismatch → try title search (CrossRef + Semantic Scholar)
    3. If all fail → flag as missing/potentially AI-generated
    """
    doi = ref.get('doi')
    raw_text = ref.get('raw_text', '')

    result = {
        'ref_number': ref.get('ref_number'),
        'verified': False,
        'confidence': 0.0,
        'source': 'not_found',
        'metadata_from_api': {},
        'mismatches': [],
        'editorial_comments': [],
        'suggested_author_fix': None,
        'author_mismatch_detail': None,
    }

    # --- Pre-checks (no API needed) ---
    if '…' in raw_text or '......' in raw_text or '……' in raw_text:
        result['editorial_comments'].append(
            "There was a discrepancy in the title compared to the original.")

    vol_match = re.search(r';\s*\d+\s*(\([^)]+\))?\s*:', raw_text)
    if vol_match and not vol_match.group(1):
        result['editorial_comments'].append("Issue number is missing.")

    if check_journal_abbreviated(raw_text):
        result['editorial_comments'].append(
            "- The journal's name should be written as an italicized full name.")

    if ref.get('has_placeholder_authors'):
        placeholders = ref.get('placeholder_authors_found', [])
        result['editorial_comments'].append(
            f"PLACEHOLDER AUTHOR NAMES detected: {', '.join(repr(p) for p in placeholders)}. "
            "Real names from CrossRef will be suggested below."
        )

    # Check author count > 6 without et al.
    ref_surnames = extract_author_surnames_from_text(raw_text)
    if len(ref_surnames) > 6 and not ref.get('has_et_al'):
        result['editorial_comments'].append(
            "Author list contains more than 6 authors. According to CMJS Vancouver style, list the first 6 authors followed by 'et al.'"
        )

    # --- Step 1: DOI lookup ---
    api_data = None
    doi_title_mismatch = False

    if doi:
        api_data = lookup_by_doi(doi)
        if api_data:
            api_title = api_data.get('title', [''])[0]
            extracted_title = extract_title_from_raw(raw_text)
            title_ratio = difflib.SequenceMatcher(
                None, extracted_title.lower()[:150], api_title.lower()[:150]
            ).ratio()
            if title_ratio < 0.55:
                doi_title_mismatch = True
                result['mismatches'].append(
                    f"DOI title mismatch (similarity {title_ratio:.2f}): "
                    f"submitted title ≠ CrossRef title → trying title search..."
                )
                result['editorial_comments'].append(
                    "The author list and Title didn't match with DOI.")
                api_data = None  # Reset, try by title
            else:
                result['source'] = 'crossref_doi'
                result['confidence'] = 1.0

    # --- Step 2: Title search (if no DOI or DOI mismatch) ---
    if api_data is None:
        extracted_title = extract_title_from_raw(raw_text)
        print(f"  → No/mismatched DOI, searching by title: '{extracted_title[:60]}...'", file=sys.stderr)
        time.sleep(0.3)  # extra politeness
        api_data = lookup_by_title(extracted_title)
        if api_data:
            match_source = api_data.get('_match_source', 'title_search')
            match_ratio = api_data.get('_match_ratio', 0.0)
            result['source'] = match_source
            result['confidence'] = match_ratio
            result['mismatches'].append(
                f"Verified via title search ({match_source}, similarity {match_ratio:.2f}) — "
                "DOI was missing or mismatched"
            )

    # --- Step 3: Flag missing/AI-generated if all fail ---
    if api_data is None:
        result['source'] = 'not_found'
        result['confidence'] = 0.0
        result['verified'] = False
        result['editorial_comments'].append(
            "❌ Cannot verify this reference — not found in CrossRef or Semantic Scholar. "
            "Please verify manually. If this reference cannot be confirmed in any database, "
            "it may be MISSING, INCORRECTLY CITED, or POTENTIALLY AI-GENERATED."
        )
        return result

    # --- Process API data ---
    result['verified'] = True
    api_title = api_data.get('title', [''])[0]
    api_container = api_data.get('container-title', [''])[0] if api_data.get('container-title') else ''
    api_volume = str(api_data.get('volume', ''))
    api_issue = str(api_data.get('issue', ''))
    api_author_list = api_data.get('author', [])
    api_doi = api_data.get('DOI', '')

    result['metadata_from_api'] = {
        'title': api_title,
        'DOI': api_doi,
        'container-title': api_container,
        'volume': api_volume,
        'issue': api_issue,
        'authors': [a.get('family', '') for a in api_author_list],
        'authors_formatted_cmjs': format_authors_cmjs(api_author_list),
    }

    cmjs_authors = format_authors_cmjs(api_author_list)

    # Author comparison
    ref_surnames = extract_author_surnames_from_text(raw_text)
    author_cmp = compare_authors(ref_surnames, api_author_list)
    if author_cmp['has_mismatch'] or ref.get('has_placeholder_authors'):
        result['author_mismatch_detail'] = author_cmp['details']
        result['suggested_author_fix'] = cmjs_authors
        mismatch_summary = [
            f"ผู้เขียนลำดับที่ {d['position']}: "
            f"'{d['in_text']}' ≠ CrossRef '{d['in_crossref']}' ({int(d['similarity']*100)}%)"
            for d in author_cmp['details']
        ]
        if mismatch_summary:
            result['editorial_comments'].append(
                "Author name mismatch with CrossRef:\n  - " + "\n  - ".join(mismatch_summary)
            )
        if cmjs_authors:
            result['editorial_comments'].append(
                f"Suggested correct author list (CMJS format): {cmjs_authors}"
            )

    # Journal full name check
    if api_container and api_container.lower() not in raw_text.lower():
        comment = "- The journal's name should be written as an italicized full name."
        if comment not in result['editorial_comments']:
            result['editorial_comments'].append(comment)
        result['mismatches'].append(f"Full journal name from API: '{api_container}'")

    return result


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Verify parsed references via CrossRef + title search.")
    parser.add_argument('input', help="Path to input JSON file from parse_references.py")
    parser.add_argument('--output', help="Path to output verification JSON file")

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    verifications = []
    refs = data.get('references', [])
    total = len(refs)

    duplicates = data.get('duplicates', [])
    if duplicates:
        print(f"\n⚠️  WARNING: {len(duplicates)} DUPLICATE reference(s) detected!", file=sys.stderr)
        for dup in duplicates:
            print(
                f"   - Ref [{dup['original_num']}] ≈ Ref [{dup['duplicate_num']}] "
                f"(similarity: {dup['similarity']})",
                file=sys.stderr
            )
        print("   → Human editor should remove duplicates and renumber.\n", file=sys.stderr)

    for i, ref in enumerate(refs):
        print(f"Verifying ref {ref['ref_number']} ({i+1}/{total})...", file=sys.stderr)
        v = verify_reference(ref)
        verifications.append(v)
        time.sleep(0.5)

    not_found = [v for v in verifications if v['source'] == 'not_found']
    title_searched = [v for v in verifications if v.get('source', '') in ('crossref_title', 'semantic_scholar')]
    print(f"\nSummary: {len(verifications) - len(not_found)}/{total} verified", file=sys.stderr)
    print(f"  Via DOI: {sum(1 for v in verifications if v.get('source') == 'crossref_doi')}", file=sys.stderr)
    print(f"  Via title search: {len(title_searched)}", file=sys.stderr)
    print(f"  Not found (missing/AI-gen): {len(not_found)}", file=sys.stderr)

    out_data = {
        'verifications': verifications,
        'duplicate_warning': duplicates,
    }

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, indent=2, ensure_ascii=False)
        print(f"Verification output saved to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(out_data, indent=2, ensure_ascii=False))
