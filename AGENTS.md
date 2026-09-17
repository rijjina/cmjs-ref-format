# 📚 CMJS Journal Formatting & Reference Verification Rules (ความรู้และกฎเกณฑ์ CMJS)

เอกสารนี้รวบรวม **ความรู้ กฎเกณฑ์ และแนวทางการทำงาน (Learned Knowledge & Rules)** ทั้งหมดของวารสาร **Chiang Mai Journal of Science (CMJS)** เพื่อให้ AI Agent ทุกเครื่องและผู้ร่วมงานทุกคนนำไปใช้ได้ทันที

---

## 🎯 1. กฎเกณฑ์ฟอร์แมตบรรณานุกรม CMJS (Vancouver Style)

* **Font & Size:** Calibri 10pt
* **ลำดับตัวเลข:** รูปแบบ `[1]`, `[2]` พร้อม Tab หลังวงเล็บ
* **รูปแบบชื่อผู้แต่ง:** `Surname I.` (นามสกุล ตามด้วยอักษรย่อชื่อต้นและจุด `.` เสมอ เช่น `Pathom-aree W.`, `Sarkar A.`)
* **กรณีผู้แต่งเกิน 6 คน (> 6 authors):** ให้แสดง 6 คนแรก แล้วตามด้วย `et al.`
* **ชื่อวารสาร:** ต้องเขียนเป็น **ชื่อเต็ม (Full Name) และใช้ตัวเอียง (Italics)** ห้ามใช้ชื่อย่อ
* **เลข Volume:** ใช้ **ตัวหนา (Bold)**
* **เลข Issue:** ต้องระบุในวงเล็บหลัง Volume เช่น `2024; 51(2): 102-110.` หากขาดหายไปต้องแจ้งเตือน `Issue number is missing.`
* **รูปแบบ DOI:** `DOI 10.xxxx/xxxx` (ตัด prefix `https://doi.org/` ออก)
* **การอ้างอิงในเนื้อหา (In-text citations):** วงเล็บเหลี่ยม `[1]`, `[2-4]`, `[1, 3, 5]`

---

## 🔍 2. ระบบการตรวจสอบ 3-Tier Verification Protocol

เมื่อทำการตรวจบรรณานุกรม ให้ใช้ลำดับขั้นตอน (Cascade) ดังนี้:

1. **Tier 1 (DOI Lookup):** ตรวจสอบผ่าน CrossRef API ด้วย DOI
2. **Tier 2 (Title Search):** หากไม่มี DOI หรือ Title ในบทความไม่ตรงกับ DOI ให้ค้นหาผ่านชื่อเรื่อง (Title) บน CrossRef Bibliographic Query และ Semantic Scholar API
3. **Tier 3 (AI-Generated / Missing Flag):** หากค้นหาไม่พบทั้ง Tier 1 และ Tier 2 ให้ Flag เตือน:
   `❌ Cannot verify this reference — not found in CrossRef or Semantic Scholar. Please verify manually. If unconfirmed, it may be MISSING, INCORRECTLY CITED, or POTENTIALLY AI-GENERATED.`

---

## 🛠️ 3. กฎการตรวจแก้ไขอัตโนมัติและการแจ้งเตือน (Editorial Feedback Rules)

1. **Auto-fix จุดชื่อย่อผู้แต่ง:** ปรับเติมจุดให้อัตโนมัติหากผู้แต่งพิมพ์ชื่อย่อไม่มีจุด (เช่น `Sarkar A` ➔ `Sarkar A.`)
2. **Auto-fix รูปแบบ Semicolon:** แปลงผู้แต่งแบบ APA/CSE Style (`Li, J.; Xu, P.;`) เป็น Vancouver Style (`Li J., Xu P.,`)
3. **Duplicate Detection:** ตรวจจับบรรณานุกรมซ้ำซ้อนด้วย Fuzzy Matching (ความใกล้เคียง ≥ 85%) พร้อมแจ้งเตือนให้ลบออกและปรับเรียงลำดับใหม่
4. **Author Surname Mismatch:** เปรียบเทียบนามสกุลผู้แต่งกับ CrossRef API เพื่อตรวจจับการพิมพ์สลับลำดับชื่อ-นามสกุล หรือชื่อจีน Pinyin
5. **Title Truncation / Ellipses:** ตรวจจับเครื่องหมาย `…` หรือข้อความที่ตัดขาดในชื่อเรื่อง

---

## 🚀 4. ทักษะอัตโนมัติที่มีใน Repo (Available Skills)

* **`cmjs-ref-check`**: ทักษะสำหรับตรวจ ดึงข้อมูล ตรวจสอบ CrossRef API และสร้างรายงาน reference check
  - `python .agents/skills/cmjs-ref-check/scripts/parse_references.py <input.docx>`
  - `python .agents/skills/cmjs-ref-check/scripts/verify_references.py <parsed.json> --output <verified.json>`
  - `python .agents/skills/cmjs-ref-check/scripts/fix_references.py <input.docx> <parsed.json> <verified.json> <output_dir>`
* **`cmjs-format`**: ทักษะจัดฟอร์แมตบทความทั้งฉบับตาม CMJS Template
  - `python .agents/skills/cmjs-format/scripts/parse_article.py <input.docx>`
  - `python .agents/skills/cmjs-format/scripts/format_article.py <parsed.json> <output_dir>`
* **`q1-reviewer2-harness`**: ทักษะ Reviewer #2 สำหรับ Q1 Journal (Brutally honest, ตรวจจับ overclaiming, N=1 fallacy, ข้อมูลขัดแย้ง, และนิติวิทยาศาสตร์การอ้างอิง AI hallucinated DOIs พร้อมตรวจสอบฟอร์แมต CMJS)
  - `python .agents/skills/q1-reviewer2-harness/scripts/audit_manuscript.py <input.docx> --output_dir <output_dir>`

