import sys
import argparse
import json
import re
import os
import difflib

try:
    import docx
except ImportError:
    print("Error: python-docx not found. Please install it using 'pip install python-docx'.", file=sys.stderr)
    sys.exit(1)

# Placeholder patterns that indicate the author didn't fill in real names
AUTHOR_PLACEHOLDER_PATTERNS = [
    r'\d+th\s+author', r'\d+nd\s+author', r'\d+rd\s+author', r'\d+st\s+author',
    r'first\s+name', r'last\s+name', r'author\s*name', r'full\s+name',
    r'surname', r'et\s+al\.\s+\(full', r'corresponding\s+author',
]

def detect_placeholder_authors(text: str) -> list:
    """Detect if any author field contains placeholder text instead of real names."""
    found = []
    for pat in AUTHOR_PLACEHOLDER_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found.append(m.group(0))
    return found

def find_duplicates(references: list) -> list:
    """Detect duplicate references using fuzzy title/text matching.
    Returns list of (original_num, duplicate_num, similarity) tuples.
    """
    duplicates = []
    for i, ref_a in enumerate(references):
        for j, ref_b in enumerate(references):
            if j <= i:
                continue
            text_a = ref_a['raw_text'].lower()[:150]
            text_b = ref_b['raw_text'].lower()[:150]
            ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
            if ratio >= 0.85:
                duplicates.append({
                    'original_num': ref_a['ref_number'],
                    'duplicate_num': ref_b['ref_number'],
                    'similarity': round(ratio, 3),
                    'original_text': ref_a['raw_text'][:120],
                    'duplicate_text': ref_b['raw_text'][:120],
                })
    return duplicates

def parse_docx(file_path: str) -> dict:
    """Parses a DOCX file to extract in-text citations and references."""
    doc = docx.Document(file_path)
    
    in_text_citations = []
    references = []
    
    in_references_section = False
    ref_pattern = re.compile(r'^\[(\d+)\]\s*(.*)')
    citation_pattern = re.compile(r'\[\d+(?:[,-]\s*\d+)*\]')
    doi_pattern = re.compile(r'(?:DOI\s*:?\s*|https?://doi\.org/)(10\.\d{4,}/[^\s]+)', re.IGNORECASE)

    current_ref = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Check for REFERENCES heading
        if not in_references_section and 'references' in text.lower() and len(text) < 50:
            in_references_section = True
            continue
            
        if not in_references_section:
            # Extract in-text citations
            citations = citation_pattern.findall(text)
            for cit in citations:
                nums_str = cit.strip('[]').replace(' ', '')
                parts = nums_str.split(',')
                for part in parts:
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        in_text_citations.extend(list(range(start, end + 1)))
                    else:
                        if part.isdigit():
                            in_text_citations.append(int(part))
        else:
            # Parse references
            match = ref_pattern.match(text)
            if match:
                if current_ref:
                    references.append(current_ref)
                
                ref_num = int(match.group(1))
                ref_text = match.group(2)
                
                # Check formatting info
                formatting = []
                for run in para.runs:
                    if run.text.strip():
                        formatting.append({
                            'text': run.text,
                            'bold': run.bold,
                            'italic': run.italic
                        })
                
                doi_match = doi_pattern.search(text)
                doi = doi_match.group(1).rstrip('.,;') if doi_match else None

                # Detect placeholder author names
                placeholder_authors = detect_placeholder_authors(text)
                
                current_ref = {
                    'ref_number': ref_num,
                    'raw_text': text,
                    'formatting_info': formatting,
                    'doi': doi,
                    'authors': [],
                    'title': "",
                    'source_type': "unknown",
                    'has_et_al': 'et al' in text.lower(),
                    'has_placeholder_authors': len(placeholder_authors) > 0,
                    'placeholder_authors_found': placeholder_authors,
                }
                
                # Basic type detection
                if 'Thesis' in text or 'thesis' in text:
                    current_ref['source_type'] = 'thesis'
                elif 'Pat. No.' in text:
                    current_ref['source_type'] = 'patent'
                elif 'Proceedings' in text:
                    current_ref['source_type'] = 'proceedings'
                elif 'Available at:' in text:
                    current_ref['source_type'] = 'online'
                elif 'Report No.' in text:
                    current_ref['source_type'] = 'report'
                elif current_ref['doi'] or 'Journal' in text or 'Vol' in text:
                    current_ref['source_type'] = 'journal'
                    
            elif current_ref:
                # Continuation of previous reference
                current_ref['raw_text'] += ' ' + text
                doi_match = doi_pattern.search(text)
                if doi_match and not current_ref['doi']:
                    current_ref['doi'] = doi_match.group(1).rstrip('.,;')
                # Check continuation for placeholder authors too
                if not current_ref['has_placeholder_authors']:
                    ph = detect_placeholder_authors(text)
                    if ph:
                        current_ref['has_placeholder_authors'] = True
                        current_ref['placeholder_authors_found'].extend(ph)

    if current_ref:
        references.append(current_ref)

    # Detect duplicates
    duplicates = find_duplicates(references)
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} potential duplicate reference(s):", file=sys.stderr)
        for dup in duplicates:
            print(f"   Ref [{dup['original_num']}] ≈ Ref [{dup['duplicate_num']}] (similarity: {dup['similarity']})", file=sys.stderr)
        
    return {
        'in_text_citations': sorted(list(set(in_text_citations))),
        'references': references,
        'duplicates': duplicates,
    }

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Parse references from a CMJS DOCX file.")
    parser.add_argument('input', help="Path to input .docx file")
    parser.add_argument('--output', help="Path to output JSON file", default=None)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File not found at {args.input}", file=sys.stderr)
        sys.exit(1)
        
    result = parse_docx(args.input)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Parsed output saved to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
