# 🎓 CMJS & Q1 Reviewer #2 Automated Peer-Review Harness
> ระบบตรวจทานบทความวิจัยระดับ Q1 และตรวจพิสูจน์การอ้างอิงอัตโนมัติ (Reference Forensics & Reviewer #2 System)

ยินดีต้อนรับสู่ระบบ **Q1 Reviewer #2 Harness** สำหรับผู้ประเมินบทความ (Peer Reviewers) และกองบรรณาธิการวารสาร **Chiang Mai Journal of Science (CMJS)**  
ระบบนี้ได้รับการออกแบบมาเพื่อให้ทุกคนในทีมสามารถใช้งาน AI Agent (Google Antigravity) ในการตรวจบทความวิจัยได้อย่างเข้มงวด มีมาตรฐานทางวิชาการระดับสากล และตรวจจับข้อผิดพลาดหรือการอ้างอิงที่ถูกสร้างขึ้นโดย AI (AI Hallucinations) ได้อย่างแม่นยำ 100%

---

## 📁 โครงสร้างโฟลเดอร์มาตรฐาน (Recommended Directory Structure)

เพื่อให้การทำงานร่วมกันเป็นระเบียบและไม่เกิดข้อผิดพลาด ให้จัดเก็บไฟล์ตามโครงสร้างดังนี้:

```text
cmjs-ref-format/
│
├── 📂 manuscripts/             ← [ใส่ไฟล์ที่นี่] วางไฟล์บทความวิจัย (.docx) ที่ต้องการตรวจที่นี่
│   └── .gitkeep                (ไฟล์ในโฟลเดอร์นี้ถูกตั้งค่า Gitignore ไว้ ไม่ต้องกังวลเรื่องข้อมูลงานวิจัยรั่วไหล)
│
├── 📂 output/                  ← [ผลลัพธ์อยู่ที่นี่] รายงานผลการประเมิน (Review Report) และผลตรวจ DOI จะถูกบันทึกที่นี่
│   ├── manuscript_audit_summary.md
│   └── manuscript_audit_data.json
│
├── 📂 .agents/                 ← โฟลเดอร์ทักษะและกฎเกณฑ์ของ Antigravity Agent
│   ├── 📂 skills/
│   │   ├── 📂 q1-reviewer2-harness/  ← ทักษะ Reviewer #2 + สคริปต์ตรวจ Crossref API อัตโนมัติ
│   │   ├── 📂 cmjs-ref-check/        ← ทักษะตรวจสอบและจัดฟอร์แมตบรรณานุกรม CMJS
│   │   └── 📂 cmjs-format/           ← ทักษะจัดหน้าเอกสารตาม Template CMJS
│   └── 📂 rules/
│       └── cmjs_rules.md
│
├── 📄 AGENTS.md                ← ดัชนีความรู้และคำสั่งลัดสำหรับ Antigravity
├── 📄 README.md                ← เอกสารคู่มือการใช้งานฉบับนี้
└── 📄 .gitignore               ← ป้องกันการอัปโหลดไฟล์บทความและไฟล์ขยะขึ้น GitHub
```

---

## 🚀 คู่มือ Git สำหรับผู้เริ่มต้น (Git Command Guide for Beginners)

ไม่ต้องกังวลหากคุณไม่มีพื้นฐานด้าน Git หรือ Terminal เลย! ทำตามคำแนะนำทีละขั้นตอนด้านล่างนี้:

### 1. การดาวน์โหลดโค้ดมาลงในเครื่องเป็นครั้งแรก (Git Clone)
เปิด **PowerShell** (หรือ Terminal) บนเครื่องของคุณ แล้วพิมพ์คำสั่ง:

```powershell
git clone https://github.com/rijjina/cmjs-ref-format.git
```
*ระบบจะสร้างโฟลเดอร์ `cmjs-ref-format` ขึ้นมาในเครื่องของคุณทันที*

---

### 2. อัปเดตข้อมูลให้เป็นรุ่นล่าสุดเสมอก่อนเริ่มทำงาน (Git Pull)
เมื่อคุณเปิดเครื่องมาทำงานในแต่ละวัน ทีมงานอาจมีการปรับปรุงระบบหรือสคริปต์ ให้ดึงการอัปเดตล่าสุดด้วยคำสั่ง:

```powershell
cd cmjs-ref-format
git pull origin master
```
*(หากระบบแจ้งว่า `Already up to date.` แสดงว่าเครื่องของคุณมีระบบล่าสุดแล้ว)*

---

### 3. ตรวจสอบสถานะว่ามีไฟล์ใดเปลี่ยนแปลงบ้าง (Git Status)
หากต้องการดูว่าในโปรเจกต์มีไฟล์อะไรเพิ่มขึ้นมา หรือไฟล์ใดถูกแก้ไข ให้พิมพ์:

```powershell
git status
```

---

### 4. การส่งการแก้ไข/พัฒนาขึ้น GitHub (Git Add, Commit, Push)
หากคุณได้ปรับปรุงกฎเกณฑ์ หรือเพิ่มฟีเจอร์ใหม่ในโฟลเดอร์ `.agents/skills/` และต้องการแบ่งปันให้เพื่อนร่วมทีม:

```powershell
# ขั้นที่ 1: เลือกไฟล์ที่ต้องการบันทึก
git add AGENTS.md .agents/skills/ README.md .gitignore

# ขั้นที่ 2: ตั้งชื่อบันทึกสิ่งที่แก้ไข (เปลี่ยนข้อความในเครื่องหมายคำพูดได้)
git commit -m "update: enhance reviewer 2 rules and references"

# ขั้นที่ 3: ส่งข้อมูลขึ้น GitHub
git push origin master
```

---

### 5. แก้ปัญหาเมื่อทำไฟล์พังแล้วอยากย้อนกลับ (Undo Changes)
หากคุณเผลอไปแก้ไขโค้ดจนเกิดปัญหา แล้วต้องการย้อนกลับไปใช้เวอร์ชันเดิมจาก GitHub:

```powershell
# ยกเลิกการแก้ไขไฟล์ที่ไม่ต้องการ แล้วกลับไปใช้ของเดิม
git restore AGENTS.md
```

---

## 🤖 วิธีสั่งงานใน Antigravity (Step-by-Step Antigravity Workflow)

### ขั้นตอนที่ 1: เปิดโปรเจกต์ใน Antigravity
1. เปิดโปรแกรม **Antigravity IDE**
2. เลือกเมนู **File ➔ Open Folder...**
3. เลือกโฟลเดอร์ `cmjs-ref-format`

### ขั้นตอนที่ 2: วางไฟล์บทความ
นำไฟล์บทความ `.docx` ที่ต้องการตรวจมาวางไว้ในโฟลเดอร์:
👉 `manuscripts/your_paper_name.docx`

### ขั้นตอนที่ 3: พิมพ์ Prompt สั่งงานในช่องแชท (Magic Prompt)
คัดลอกข้อความด้านล่างนี้แล้ววางลงในช่องแชทของ Antigravity:

```text
Please act as Reviewer #2 using the q1-reviewer2-harness skill.
Review the manuscript located at:
manuscripts/your_paper_name.docx

Execute the following tasks:
1. Run the forensic audit on all references and citations.
2. Check for AI-hallucinated or corrupted DOIs against real academic databases.
3. Critically analyze the scientific rigor, potential overclaiming (e.g. N=1 endurance limit, displacement vs stress control confounding), and data contradictions.
4. Verify compliance with CMJS reference guidelines.
5. Provide a full Q1 Reviewer #2 report and save the summary to the output/ folder.
```

### ขั้นตอนที่ 4: ตรวจสอบผลลัพธ์
Antigravity จะเริ่มทำงานอัตโนมัติ:
1. รันสคริปต์ `audit_manuscript.py` ตรวจสอบฐานข้อมูล Crossref และ doi.org
2. สร้างตารางวิเคราะห์ความถูกต้องของ DOI ทุกรายการ
3. เขียนรายงานประเมินบทความ (Reviewer #2 Report) ฉบับสมบูรณ์ในแชท และบันทึกรายงานสรุปไว้ในโฟลเดอร์ `output/`

---

## 💡 ข้อแนะนำสำคัญทางวิชาการ (Academic Best Practices & Recommendations)

1. **ความลับของบทความ (Confidentiality):**  
   บทความที่อยู่ระหว่างการประเมินถือเป็นความลับทางวิชาการ ห้ามนำไฟล์บทความจริงอัปโหลดขึ้น Public Repository บน GitHub โดยเด็ดขาด ไฟล์ `.gitignore` ในโปรเจกต์นี้ได้รับการตั้งค่าไว้แล้วเพื่อป้องกันไม่ให้ไฟล์ `.docx` และ `.pdf` ในโฟลเดอร์ `manuscripts/` ถูก Commit โดยไม่ตั้งใจ
2. **การตรวจจับ AI Hallucination:**  
   หากผู้แต่งใช้ Generative AI (เช่น ChatGPT, Claude) ในการจัดฟอร์แมตเอกสาร มักจะพบปัญหา:
   - เลขท้ายของ DOI เพี้ยน (เช่น สลับตัวเลขท้าย หรือนำเลขหน้าของบทความมาใส่เป็น DOI)
   - DOI ถูกต้อง แต่เป็นของบทความอื่นที่ไม่เกี่ยวข้องเลย (Mismatched DOI)
   - สคริปต์ใน Harness นี้จะค้นหาและระบุปัญหาเหล่านี้ในตารางอย่างชัดเจน
3. **การประเมินอย่างสร้างสรรค์ (Constructive Critique):**  
   หน้าที่ของ Reviewer #2 คือการเป็นผู้พิทักษ์คุณภาพทางวิชาการ (Academic Rigor) ชี้จุดบกพร่องทางวิทยาศาสตร์อย่างตรงไปตรงมา ชัดเจน แต่ต้องคงไว้ซึ่งความสุภาพ และมีข้อเสนอแนะที่ผู้แต่งสามารถนำไปปรับปรุงแก้ไขได้จริง (Actionable Directives)
4. **กฎเกณฑ์เฉพาะของ CMJS:**  
   วารสาร CMJS ใช้ระบบ **Vancouver Style** โดยมีข้อบังคับสำคัญคือ:
   - **ไม่ต้องใส่ชื่อบทความ (Article Title) ในรายการบรรณานุกรมวารสาร**
   - รูปแบบ: `[เลข] นามสกุล ชื่อย่อ., ชื่อย่อวารสาร., ปี; เล่ม(ฉบับ): หน้า-หน้า. DOI 10.xxxx/xxxx`
