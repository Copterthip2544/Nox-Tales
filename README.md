# Frame Tales

ชื่อช่องที่ยืนยัน: **Frame Tales** — **NOX** เป็นมาสคอตและผู้เล่าเรื่อง ใช้ชื่อ Frame Tales ในแบนเนอร์ ชื่อคลิป และคำอธิบายช่องทั้งหมด

[ไฟล์โปรไฟล์และแบนเนอร์พร้อมใช้](branding/README.md)

ระบบเตรียมผลิตเรื่องเล่า fiction horror ภาษาไทย

## ตรวจ Gemini API

1. เพิ่ม Repository secret ชื่อ `GEMINI_API_KEY` ที่ Settings → Secrets and variables → Actions
2. ไปที่ Actions → **Check Gemini connection**
3. Workflow รันเมื่อเพิ่มหรือแก้ไฟล์ตรวจการเชื่อมต่อบน main หรือกด Run workflow เพื่อรันเอง
4. เปิดผล run ดู Summary และดาวน์โหลด artifact `gemini-model-catalogue`

ขั้นนี้เรียกเฉพาะ `GET /v1beta/models` ไม่สร้างข้อความ ภาพ หรือเสียง ไม่ใส่คีย์ใน URL และไม่บันทึกคีย์ในไฟล์ผลลัพธ์
โมเดลที่ชื่อมี `tts` เป็นเพียงตัวเลือกให้ตรวจต่อ ยังไม่ยืนยันว่าอ่านไทยหรือทำเสียงเด็ก/คนแก่ได้ ต้องทดลองแยกหลังเลือกโมเดลจริง
คีย์อยู่ใน GitHub Actions เท่านั้น การเพิ่ม Secret ไม่ได้ส่งคีย์มาให้แชตหรือเชื่อม Codex Environment อัตโนมัติ

## เมื่อไม่ผ่าน

- ไม่พบ secret: ตรวจชื่อ `GEMINI_API_KEY` และให้เป็น Repository secret
- HTTP 400/401/403: ตรวจคีย์ ข้อจำกัดคีย์ และสิทธิ์ API ของ Google project
- HTTP 429: ตรวจ quota และรอก่อนลองใหม่
- เครือข่าย/บริการขัดข้อง: ลองใหม่ภายหลัง

## ทดลองเสียงไทย

เพิ่ม workflow **Preview Thai character voices** สำหรับ `gemini-3.8-flash-tts` แล้ว
รันด้วยมือเท่านั้น สร้างตัวอย่าง Nox / ผู้จัดการ / ลิน ได้สูงสุด 3 คำขอ ไม่สร้างบทเต็ม
อ่านวิธีใช้งานที่ [คู่มือทดลองเสียง](docs/voice-preview.md) และฟังผลจริงก่อนเลือกเสียง
ยังไม่มีการรันสร้างตัวอย่างเสียงในขั้นเตรียมนี้ และไม่มี API key ใน repository
