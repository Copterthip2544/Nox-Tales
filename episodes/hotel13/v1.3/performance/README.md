# วิธีใช้คำกำกับอารมณ์กับ Gemini 3.8 TTS

- ข้อความอ่านจริง: performance.json → events ที่ type เป็น speech → text
- น้ำเสียงต่อประโยค: ใส่ performance.style ลง parts[].speech_metadata.style
- เลือกเสียงจาก performance.voice ตามที่ผู้ใช้อนุมัติ ไม่เปลี่ยน voice เพื่อเปลี่ยนอารมณ์
- ถ้า voice เป็น null ให้หยุดและเลือกเสียงก่อน ห้าม fallback เป็นเสียงคนอื่น
- ไม่ส่งชื่อผู้พูด อารมณ์ ระดับความเข้ม คำกำกับ หรือรหัส E เป็นข้อความอ่าน
- ไม่อ่าน events ที่เป็น direction และไม่ให้ Nox บรรยายทับบทสนทนา
- post_pause_ms เป็นแนวทางตอนตัดต่อ ให้หักช่วงเงียบที่ติดมากับไฟล์ออกก่อน ไม่บวกซ้ำและไม่ใส่ท้ายทุกประโยคโดยไม่ฟัง
- อารมณ์กลัวไม่จำเป็นต้องตะโกน อารมณ์เศร้าไม่จำเป็นต้องสะอื้นทุกประโยค ให้ความชัดภาษาไทยมาก่อน
- ทำเสียงโทรศัพท์ ระยะเสียง และ reverb ตอนมิกซ์ แยกจากการแสดงอารมณ์

ตัวอย่างรูปแบบคำขอ (เป็นแม่แบบ ยังไม่ได้เรียก API):
```json
{
  "contents": [{
    "role": "user",
    "parts": [{
      "text": "ฉันจะช่วยพาลูกคุณออกไปค่ะ",
      "speech_metadata": {
        "style": "Maintain the approved original Kore identity: Thai woman about 25. Sincere reassurance and determination, warm adult voice, quietly committed."
      }
    }]
  }],
  "generationConfig": {
    "responseModalities": ["AUDIO"],
    "speechConfig": {"voiceConfig": {"voice": "Kore"}}
  }
}
```

ระบบ preview_voices.py เดิมยังใช้ style ระดับตัวอย่างใน config/voice_samples.json ไม่ได้อ่าน performance.json อัตโนมัติ ชุดกำกับนี้เตรียมไว้สำหรับตัวสร้างเสียงบทเต็มหรือชุดทดลองบทสนทนาขั้นถัดไป ยังไม่มีการสร้างเสียงใหม่ในงานนี้
