-- Bot Settings: editable configuration per company
-- Stores lists/dicts that control chatbot behavior (phrases, keywords, etc.)
-- Run this once on your Supabase project.

create table if not exists bot_settings (
  id           uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  setting_key  text not null,
  setting_value jsonb not null,
  updated_at   timestamptz default now(),
  unique(company_code, setting_key)
);

create index if not exists idx_bot_settings_company on bot_settings(company_code);

-- ── Seed defaults for DEVES ───────────────────────────────────────────────────

insert into bot_settings(company_code, setting_key, setting_value) values

('DEVES', 'no_answer_phrases', '["ยังไม่มีข้อมูล","ไม่มีข้อมูลส่วนนี้","ไม่พบข้อมูล","ไม่มีข้อมูลเกี่ยวกับ","ไม่มีข้อมูลในระบบ","ไม่มีในฐานข้อมูล"]'),

('DEVES', 'clarify_phrases', '["หมายถึงอะไรครับ","หมายถึงอะไรคะ","ต้องการข้อมูลส่วนไหน","ต้องการทราบข้อมูลส่วนไหน","กรุณาระบุเพิ่มเติม","ขอทราบเพิ่มเติม"]'),

('DEVES', 'ambiguous_keywords', '{
  "เบอร์":   ["เบอร์โทรศัพท์","เบอร์กรมธรรม์","เบอร์เคลม","เบอร์มือถือ"],
  "รหัส":   ["รหัสกรมธรรม์","รหัสอ้างอิง","รหัสสาขา"],
  "ราคา":   ["ราคาเบี้ยประกัน","ราคาซ่อม","ราคาต่ออายุ"],
  "ติดต่อ": ["ช่องทางโทรศัพท์","ช่องทางอีเมล","ที่อยู่สำนักงาน"],
  "ที่อยู่": ["ที่อยู่สำนักงานใหญ่","ที่อยู่สาขา"],
  "เอกสาร": ["เอกสารการเคลม","เอกสารต่อกรมธรรม์","เอกสารใบแจ้งหนี้"]
}'),

('DEVES', 'clear_question_words', '["ที่ไหน","อยู่ที่ไหน","ได้ที่ไหน","อย่างไร","ยังไง","คืออะไร","หมายความว่าอะไร","ทำอะไร","ทำได้ไหม","ทำยังไง","เมื่อไหร่","เท่าไหร่","กี่บาท","คือใคร","มีไหม","ใช่ไหม"]')

on conflict(company_code, setting_key) do nothing;
