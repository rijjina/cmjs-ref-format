---
name: cmjs-format
description: >-
  Use this skill when the user asks to format a manuscript/article according to
  CMJS (Chiang Mai Journal of Science) template. Reads a .docx submission file,
  extracts content sections, and reformats into the CMJS template with correct
  fonts, sizes, margins, and section structure.
---

# CMJS Format Skill

This skill formats an article into the Chiang Mai Journal of Science (CMJS) template.

## Instructions

When the user asks to format a manuscript/article:

1. **Ask for the file path**: Ask the user for the absolute path to the `.docx` submission file if they haven't provided it.
2. **Extract content**: Run the parse script on the provided file:
   `python .agents/skills/cmjs-format/scripts/parse_article.py <input.docx>`
   This creates a JSON file with the article structure.
3. **Review**: Review the parsed structure output with the user. Make sure all key sections (Title, Authors, Abstract, Introduction, etc.) were correctly identified.
4. **Format**: Run the formatting script:
   `python .agents/skills/cmjs-format/scripts/format_article.py <parsed_article.json> <output_dir>`
   This uses `resources/cmjs-template.docx` to generate the formatted output file.
5. **Present**: Present the formatted file (located at `<output_dir>/<original_filename>_formatted.docx`) to the user.
6. **Iterate**: If the user finds formatting issues or sections that didn't map correctly, manually adjust the JSON and rerun step 4, or guide them through manual tweaks.

## Important Notes

* The parsing script uses heuristics to identify sections (e.g., text length, bold formatting, common CMJS keywords). 
* The template uses Letter size (8.5x11in), Calibri font (10pt for body, 16pt for Title), and specific margin settings (Left=1.0in, Right=0.92in, Top=0.71in, Bottom=0.69in).
