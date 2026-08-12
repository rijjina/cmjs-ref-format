import sys
import json
import argparse
import os
from docx import Document

sys.stdout.reconfigure(encoding='utf-8')

KNOWN_SECTIONS = [
    "ABSTRACT", "HIGHLIGHTS", "INTRODUCTION", "1. INTRODUCTION",
    "MATERIALS AND METHODS", "2. MATERIALS AND METHODS",
    "RESULTS AND DISCUSSION", "3. RESULTS AND DISCUSSION",
    "CONCLUSIONS", "4. CONCLUSIONS", "ACKNOWLEDGEMENTS",
    "AUTHOR CONTRIBUTIONS", "CONFLICT OF INTEREST STATEMENT",
    "DECLARATION OF USE OF GENERATIVE AI", "ETHICAL GUIDELINES",
    "FUNDING", "REFERENCES"
]

def is_heading(text, runs):
    """Heuristic to detect if a paragraph is a heading."""
    text = text.strip()
    if not text:
        return False
    
    # Check if exact match to known section (case-insensitive)
    upper_text = text.upper()
    if upper_text in KNOWN_SECTIONS or upper_text.startswith("KEYWORDS:"):
        return True
        
    # Check sub-sections like 2.1, 2.1.1
    parts = text.split()
    if parts and any(parts[0].startswith(str(i)+".") for i in range(1, 10)):
        return True
        
    # Check if mostly bold and short
    if len(text) < 100:
        bold_len = sum(len(r.text) for r in runs if r.bold)
        if bold_len > len(text) * 0.5:  # more than 50% bold
            return True

    return False

def extract_runs(paragraph):
    """Extract formatting info from paragraph runs."""
    run_data = []
    for run in paragraph.runs:
        if not run.text:
            continue
        run_data.append({
            "text": run.text,
            "bold": bool(run.bold),
            "italic": bool(run.italic),
            "underline": bool(run.underline),
            "superscript": bool(run.font.superscript),
            "subscript": bool(run.font.subscript)
        })
    return run_data

def parse_document(file_path):
    doc = Document(file_path)
    
    article_data = {
        "title": None,
        "authors": [],
        "affiliations": [],
        "corresponding_author": None,
        "sections": []
    }
    
    current_section = {"section_name": "FrontMatter", "paragraphs": []}
    
    state = "TITLE"
    
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
            
        # Title logic
        if state == "TITLE":
            article_data["title"] = extract_runs(p)
            state = "AUTHORS"
            continue
            
        # Authors logic
        if state == "AUTHORS":
            if p.runs and p.runs[0].bold and not text.startswith("["):
                article_data["authors"].append(extract_runs(p))
                continue
            else:
                state = "AFFILIATIONS"
        
        # Affiliations logic
        if state == "AFFILIATIONS":
            if text.startswith("["):
                article_data["affiliations"].append(extract_runs(p))
                continue
            elif text.startswith("*") or text.lower().startswith("author for correspondence"):
                article_data["corresponding_author"] = extract_runs(p)
                state = "BODY"
                continue
            elif is_heading(text, p.runs):
                state = "BODY"
            else:
                # If neither, maybe category or something else, default to body transition
                if text.upper() == "CATEGORY":
                    continue # Skip category marker if standalone
                state = "BODY"
                
        if state == "BODY":
            if is_heading(text, p.runs):
                if current_section["paragraphs"] or current_section["section_name"] != "FrontMatter":
                    article_data["sections"].append(current_section)
                current_section = {"section_name": text, "paragraphs": []}
            else:
                current_section["paragraphs"].append(extract_runs(p))

    # Append last section
    if current_section["paragraphs"]:
        article_data["sections"].append(current_section)
        
    return article_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse article to JSON.")
    parser.add_argument("input", help="Path to input .docx")
    parser.add_argument("--output", help="Path to output .json (defaults to stdout)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File {args.input} does not exist.", file=sys.stderr)
        sys.exit(1)
        
    try:
        data = parse_document(args.input)
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"Parsed structure written to {args.output}")
        else:
            print(json_str)
            
    except Exception as e:
        print(f"Error parsing document: {e}", file=sys.stderr)
        sys.exit(1)
