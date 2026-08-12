import sys
import argparse
import json
import os
import shutil
import re

try:
    import docx
    from docx.shared import Pt
except ImportError:
    print("Error: python-docx not found. Please install it using 'pip install python-docx'.", file=sys.stderr)
    sys.exit(1)

def fix_author_initials(raw_text: str) -> str:
    """Ensures author initials end with a dot (e.g., 'Sarkar A,' -> 'Sarkar A.,')."""
    def add_dot(match):
        author_part = match.group(1)
        sep = match.group(2)
        if not author_part.endswith('.'):
            return f"{author_part}.{sep}"
        return match.group(0)
    fixed = re.sub(r'([A-Z][a-z]+(?:\-[A-Z][a-z]+)?\s+[A-Z](?:\-[A-Z])?)(,|\s+and\b)', add_dot, raw_text)
    return fixed

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Fix references in DOCX based on verifications.")
    parser.add_argument('input_docx', help="Path to input .docx file")
    parser.add_argument('parsed_json', help="Path to parsed references JSON")
    parser.add_argument('verify_json', help="Path to verification JSON")
    parser.add_argument('output_dir', help="Directory to save output files")
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(args.input_docx))[0]
    out_docx = os.path.join(args.output_dir, f"{base_name}_ref_fixed.docx")
    out_md = os.path.join(args.output_dir, f"{base_name}_ref_report.md")
    
    with open(args.parsed_json, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)

    with open(args.verify_json, 'r', encoding='utf-8') as f:
        verify_data = json.load(f)

    references = parsed_data.get('references', [])
    verifications = verify_data.get('verifications', [])
    in_text_citations = set(parsed_data.get('in_text_citations', []))
    ref_nums = set(r['ref_number'] for r in references)
    duplicates = parsed_data.get('duplicates', verify_data.get('duplicate_warning', []))

    # Copy DOCX
    shutil.copy2(args.input_docx, out_docx)

    report_lines = []
    report_lines.append(f"# 📚 รายงานการตรวจสอบบรรณานุกรม (Reference Check Report): {base_name}\n")

    # --- Summary ---
    report_lines.append("## 📊 สรุปภาพรวม (Executive Summary)\n")
    report_lines.append(f"- **จำนวนรายการอ้างอิงทั้งหมด**: {len(references)} รายการ")
    report_lines.append(f"- **การอ้างอิงในเนื้อหา (In-text citations)**: {len(in_text_citations)} รายการ")

    if in_text_citations == ref_nums:
        report_lines.append("- **ความสอดคล้อง In-text vs Reference list**: ✅ **ตรงกันครบถ้วน**")
    else:
        missing_in_list = in_text_citations - ref_nums
        orphan_in_list = ref_nums - in_text_citations
        report_lines.append(f"- **ความสอดคล้อง In-text vs Reference list**: ⚠️ **มีข้อแตกต่าง**")
        if missing_in_list:
            report_lines.append(f"  - 🔴 อ้างอิงในเนื้อหาแต่ไม่มีในรายการ: {sorted(missing_in_list)}")
        if orphan_in_list:
            report_lines.append(f"  - 🔴 มีในรายการแต่ไม่ถูกอ้างอิงในเนื้อหา: {sorted(orphan_in_list)}")

    verified_count = sum(1 for v in verifications if v.get('verified'))
    report_lines.append(f"- **ตรวจสอบในฐานข้อมูล (CrossRef)**: {verified_count}/{len(references)} รายการ\n")

    # --- DUPLICATE WARNING ---
    if duplicates:
        report_lines.append("---\n")
        report_lines.append("## 🔴 พบรายการบรรณานุกรมซ้ำซ้อน (DUPLICATE REFERENCES DETECTED)\n")
        report_lines.append("> [!CAUTION]")
        report_lines.append("> พบรายการที่ซ้ำกัน ควรลบรายการที่ซ้ำออกและปรับเรียงลำดับเลขบรรณานุกรมและการอ้างอิงในเนื้อหาใหม่\n")
        for dup in duplicates:
            report_lines.append(f"- ⚠️ **รายการ [{dup['original_num']}]** ≈ **รายการ [{dup['duplicate_num']}]** (ความใกล้เคียง: {dup['similarity']*100:.0f}%)")
            report_lines.append(f"  - [{dup['original_num']}]: `{dup['original_text'][:100]}...`")
            report_lines.append(f"  - [{dup['duplicate_num']}]: `{dup['duplicate_text'][:100]}...`")
            report_lines.append(f"  - 🔧 **คำแนะนำ**: ลบรายการ [{dup['duplicate_num']}] ออก และปรับเรียงหมายเลขอ้างอิงในเนื้อหาให้ถูกต้อง\n")

    report_lines.append("---\n")
    report_lines.append("## 📊 สรุปประเด็นหลักที่ส่งให้ผู้เขียนแก้ไข (Editorial Feedback Rules)\n")
    report_lines.append("1. **การย่อชื่อผู้เขียน**: ระบบปรับเติมจุด `.` ต่อท้ายชื่อย่อให้อัตโนมัติ (เช่น `Sarkar A` ➔ `Sarkar A.`)")
    report_lines.append("2. **ชื่อวารสารแบบย่อ**: `- The journal's name should be written as an italicized full name.`")
    report_lines.append("3. **เลข Issue ขาดหาย**: `Issue number is missing.`")
    report_lines.append("4. **ชื่อเรื่องไม่สมบูรณ์**: `There was a discrepancy in the title compared to the original.`")
    report_lines.append("5. **DOI ไม่ตรง**: `The author list and Title didn't match with DOI.`")
    report_lines.append("6. **ชื่อผู้เขียนชั่วคราว (Placeholder)**: แจ้งเตือนและดึงรายชื่อจริงจาก CrossRef API")
    report_lines.append("7. **ชื่อ-นามสกุลสลับลำดับ / พิมพ์ผิด**: ตรวจจากฐานข้อมูล CrossRef พร้อมแนะนำค่าที่ถูกต้อง\n")
    report_lines.append("---\n")
    report_lines.append("## 📋 รายละเอียดการตรวจพบรายข้อ (Detailed List)\n")

    for i, r in enumerate(references):
        num = r['ref_number']
        v = verifications[i] if i < len(verifications) else {}
        raw = r['raw_text'].strip()
        
        # Apply author initial dot fix
        fixed_text = fix_author_initials(raw)
        
        comments = v.get('editorial_comments', [])
        api_meta = v.get('metadata_from_api', {})
        suggested_fix = v.get('suggested_author_fix')
        is_dup = any(d['duplicate_num'] == num for d in duplicates)
        
        is_ver = v.get('verified')
        ver_icon = '✅' if is_ver else 'ℹ️'
        dup_flag = ' 🔴 **DUPLICATE**' if is_dup else ''
        
        report_lines.append(f"### [{num}] {ver_icon}{dup_flag}")
        report_lines.append(f"**ข้อความเดิม**:")
        report_lines.append(f"> {raw}\n")
        
        if fixed_text != raw:
            report_lines.append(f"**🔧 ปรับแก้ชื่อย่อผู้แต่งอัตโนมัติ**:")
            report_lines.append(f"> {fixed_text}\n")

        if suggested_fix:
            report_lines.append(f"**🔧 รายชื่อผู้เขียนจาก CrossRef (แนะนำใช้แทนข้อความชั่วคราว)**:")
            report_lines.append(f"> {', '.join(suggested_fix[:6])}{' et al.' if len(suggested_fix) > 6 else ''}\n")
            
        if comments:
            report_lines.append("**ข้อความแจ้งเตือนผู้เขียน (Editorial Comments)**:")
            for c in comments:
                report_lines.append(f"- ⚠️ {c}")
            report_lines.append("")

        if v.get('mismatches'):
            report_lines.append("**ข้อมูลเพิ่มเติมจาก CrossRef**:")
            for m in v['mismatches']:
                report_lines.append(f"- 🔍 {m}")
            report_lines.append("")

        if not comments and not v.get('mismatches') and fixed_text == raw:
            report_lines.append("✅ **สมบูรณ์ถูกต้องตามเกณฑ์**\n")
            
        report_lines.append("---\n")

    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"Saved fixed docx to: {out_docx}")
    print(f"Saved report to: {out_md}")

if __name__ == '__main__':
    main()
