/** UI 다국어 사전 — 외국인 페르소나 선택 시 화면 전체를 해당 언어로 전환한다.
 *
 * 언어 선정 근거(2025 법무부 등록외국인·고용허가제 E-9·유학생 통계):
 * 중국(47.8만)·베트남(29.4만)·네팔(8.9만)·우즈베키스탄·캄보디아·태국 순 +
 * E-9 상위(캄보디아·네팔 각 4.7만, 베트남), 유학생 상위(우즈벡·몽골·네팔·미얀마).
 *
 * 번역 방침:
 * - 계약서 원문·근거(원문 인용)·확인 질문은 한국어 유지 — 원문 대조와
 *   상대방(한국인)에게 보여주는 용도이기 때문. 대신 라벨과 안내문으로 설명한다.
 * - 저자원 언어(km/my/si/bn/ne 등)는 AI 초벌 번역 — 원어민 검수 전까지
 *   기획서에 '실험적 지원'으로 표기할 것.
 */

export type LangCode =
  | 'ko' | 'en' | 'zh' | 'vi' | 'th' | 'id' | 'tl' | 'ne'
  | 'km' | 'my' | 'mn' | 'uz' | 'si' | 'bn' | 'ru' | 'ja'

export const LANGUAGES: Array<{ id: LangCode; label: string }> = [
  { id: 'en', label: 'English' },
  { id: 'zh', label: '中文' },
  { id: 'vi', label: 'Tiếng Việt' },
  { id: 'th', label: 'ไทย' },
  { id: 'id', label: 'Bahasa Indonesia' },
  { id: 'tl', label: 'Filipino' },
  { id: 'ne', label: 'नेपाली' },
  { id: 'km', label: 'ខ្មែរ' },
  { id: 'my', label: 'မြန်မာ' },
  { id: 'mn', label: 'Монгол' },
  { id: 'uz', label: 'Oʻzbekcha' },
  { id: 'si', label: 'සිංහල' },
  { id: 'bn', label: 'বাংলা' },
  { id: 'ru', label: 'Русский' },
  { id: 'ja', label: '日本語' },
  { id: 'ko', label: '쉬운 한국어' },
]

type UIKey =
  | 'analysisDone' | 'analyzingLive' | 'liveHint' | 'verifyingNote'
  | 'headlineTotal' | 'headlineNeed' | 'danger' | 'caution' | 'safe'
  | 'checkFirst' | 'standardClause' | 'standardClauseLong' | 'all'
  | 'copyAllQuestions' | 'evidence' | 'noClauses' | 'seeDetail' | 'finish'
  | 'backToSummary' | 'clauseList' | 'explainSimply' | 'whyCheck'
  | 'originalText' | 'askOther' | 'askKoreanHint' | 'otherClauses' | 'finishDetail'
  | 'progressTitle' | 'cancel'

const UI: Record<LangCode, Record<UIKey, string>> = {
  ko: {
    analysisDone: '분석 완료', analyzingLive: '조항 {done}/{total}개 분석 중', liveHint: '끝난 조항부터 먼저 보여드려요',
    verifyingNote: 'AI 검증이 진행 중이에요 — 완료되면 결과가 확정돼요',
    headlineTotal: '전체 {total}개 조항 중', headlineNeed: '확인이 필요한 조항이 {need}개 있어요',
    danger: '위험', caution: '주의', safe: '안전',
    checkFirst: '가장 먼저 확인하세요', standardClause: '표준 조항', standardClauseLong: '표준적인 조항이에요', all: '전체',
    copyAllQuestions: '질문 전체 복사', evidence: '근거', noClauses: '해당하는 조항이 없어요', seeDetail: '자세히 보기', finish: '결과 활용하고 마치기',
    backToSummary: '결과 요약으로', clauseList: '조항 목록', explainSimply: '쉽게 설명하면', whyCheck: '왜 확인해야 하나요?',
    originalText: '계약서 원문', askOther: '계약 상대방에게 물어보세요', askKoreanHint: '질문은 한국어 그대로 화면을 보여주셔도 돼요',
    otherClauses: '다른 조항 보기', finishDetail: '확인 끝내고 결과 활용하기',
    progressTitle: '계약서를 꼼꼼히 살펴보고 있어요', cancel: '분석 취소',
  },
  en: {
    analysisDone: 'Analysis complete', analyzingLive: 'Analyzing clause {done}/{total}', liveHint: 'Finished clauses appear first',
    verifyingNote: 'AI verification in progress — results are finalized when it completes',
    headlineTotal: 'Out of {total} clauses,', headlineNeed: '{need} need your attention',
    danger: 'Risk', caution: 'Caution', safe: 'Safe',
    checkFirst: 'Check this first', standardClause: 'Standard clause', standardClauseLong: 'This is a standard clause', all: 'All',
    copyAllQuestions: 'Copy all questions', evidence: 'Evidence', noClauses: 'No matching clauses', seeDetail: 'See details', finish: 'Use results & finish',
    backToSummary: 'Back to summary', clauseList: 'Clauses', explainSimply: 'In simple terms', whyCheck: 'Why check this?',
    originalText: 'Original contract text (Korean)', askOther: 'Ask the other party', askKoreanHint: 'Questions are in Korean — you can show this screen directly',
    otherClauses: 'Other clauses', finishDetail: 'Done — use results',
    progressTitle: 'Reviewing your contract carefully', cancel: 'Cancel analysis',
  },
  zh: {
    analysisDone: '分析完成', analyzingLive: '正在分析条款 {done}/{total}', liveHint: '已完成的条款会先显示',
    verifyingNote: 'AI 验证进行中 — 完成后结果将最终确定',
    headlineTotal: '共 {total} 个条款中，', headlineNeed: '有 {need} 个需要您注意',
    danger: '危险', caution: '注意', safe: '安全',
    checkFirst: '请先确认这一条', standardClause: '标准条款', standardClauseLong: '这是标准条款', all: '全部',
    copyAllQuestions: '复制全部问题', evidence: '依据', noClauses: '没有符合的条款', seeDetail: '查看详情', finish: '使用结果并完成',
    backToSummary: '返回摘要', clauseList: '条款列表', explainSimply: '简单来说', whyCheck: '为什么要确认？',
    originalText: '合同原文（韩语）', askOther: '向对方询问', askKoreanHint: '问题为韩语 — 可以直接把屏幕出示给对方',
    otherClauses: '查看其他条款', finishDetail: '完成确认，使用结果',
    progressTitle: '正在仔细审查您的合同', cancel: '取消分析',
  },
  vi: {
    analysisDone: 'Phân tích hoàn tất', analyzingLive: 'Đang phân tích điều khoản {done}/{total}', liveHint: 'Điều khoản xong sẽ hiển thị trước',
    verifyingNote: 'AI đang kiểm chứng — kết quả sẽ được xác nhận khi hoàn tất',
    headlineTotal: 'Trong tổng số {total} điều khoản,', headlineNeed: 'có {need} điều khoản cần chú ý',
    danger: 'Nguy hiểm', caution: 'Cẩn thận', safe: 'An toàn',
    checkFirst: 'Kiểm tra điều này trước', standardClause: 'Điều khoản tiêu chuẩn', standardClauseLong: 'Đây là điều khoản tiêu chuẩn', all: 'Tất cả',
    copyAllQuestions: 'Sao chép tất cả câu hỏi', evidence: 'Căn cứ', noClauses: 'Không có điều khoản phù hợp', seeDetail: 'Xem chi tiết', finish: 'Dùng kết quả & kết thúc',
    backToSummary: 'Về trang tóm tắt', clauseList: 'Danh sách điều khoản', explainSimply: 'Nói một cách đơn giản', whyCheck: 'Vì sao cần kiểm tra?',
    originalText: 'Nguyên văn hợp đồng (tiếng Hàn)', askOther: 'Hỏi bên kia hợp đồng', askKoreanHint: 'Câu hỏi bằng tiếng Hàn — bạn có thể đưa màn hình này cho họ xem',
    otherClauses: 'Điều khoản khác', finishDetail: 'Xong — dùng kết quả',
    progressTitle: 'Đang xem kỹ hợp đồng của bạn', cancel: 'Hủy phân tích',
  },
  th: {
    analysisDone: 'วิเคราะห์เสร็จสิ้น', analyzingLive: 'กำลังวิเคราะห์ข้อ {done}/{total}', liveHint: 'ข้อที่เสร็จแล้วจะแสดงก่อน',
    verifyingNote: 'AI กำลังตรวจสอบ — ผลจะยืนยันเมื่อเสร็จสิ้น',
    headlineTotal: 'จากทั้งหมด {total} ข้อ', headlineNeed: 'มี {need} ข้อที่ควรตรวจสอบ',
    danger: 'อันตราย', caution: 'ระวัง', safe: 'ปลอดภัย',
    checkFirst: 'ตรวจสอบข้อนี้ก่อน', standardClause: 'ข้อสัญญามาตรฐาน', standardClauseLong: 'นี่คือข้อสัญญามาตรฐาน', all: 'ทั้งหมด',
    copyAllQuestions: 'คัดลอกคำถามทั้งหมด', evidence: 'หลักฐาน', noClauses: 'ไม่มีข้อที่ตรงกัน', seeDetail: 'ดูรายละเอียด', finish: 'ใช้ผลลัพธ์และเสร็จสิ้น',
    backToSummary: 'กลับไปหน้าสรุป', clauseList: 'รายการข้อสัญญา', explainSimply: 'อธิบายง่าย ๆ', whyCheck: 'ทำไมต้องตรวจสอบ?',
    originalText: 'ข้อความสัญญาต้นฉบับ (ภาษาเกาหลี)', askOther: 'ถามอีกฝ่าย', askKoreanHint: 'คำถามเป็นภาษาเกาหลี — แสดงหน้าจอนี้ให้เขาดูได้เลย',
    otherClauses: 'ข้ออื่น ๆ', finishDetail: 'เสร็จแล้ว — ใช้ผลลัพธ์',
    progressTitle: 'กำลังตรวจสัญญาของคุณอย่างละเอียด', cancel: 'ยกเลิกการวิเคราะห์',
  },
  id: {
    analysisDone: 'Analisis selesai', analyzingLive: 'Menganalisis pasal {done}/{total}', liveHint: 'Pasal yang selesai tampil lebih dulu',
    verifyingNote: 'Verifikasi AI sedang berjalan — hasil final setelah selesai',
    headlineTotal: 'Dari total {total} pasal,', headlineNeed: '{need} pasal perlu diperhatikan',
    danger: 'Bahaya', caution: 'Hati-hati', safe: 'Aman',
    checkFirst: 'Periksa ini dulu', standardClause: 'Pasal standar', standardClauseLong: 'Ini pasal standar', all: 'Semua',
    copyAllQuestions: 'Salin semua pertanyaan', evidence: 'Dasar', noClauses: 'Tidak ada pasal yang cocok', seeDetail: 'Lihat detail', finish: 'Gunakan hasil & selesai',
    backToSummary: 'Kembali ke ringkasan', clauseList: 'Daftar pasal', explainSimply: 'Secara sederhana', whyCheck: 'Mengapa perlu diperiksa?',
    originalText: 'Teks asli kontrak (bahasa Korea)', askOther: 'Tanyakan ke pihak lain', askKoreanHint: 'Pertanyaan dalam bahasa Korea — tunjukkan layar ini langsung',
    otherClauses: 'Pasal lainnya', finishDetail: 'Selesai — gunakan hasil',
    progressTitle: 'Memeriksa kontrak Anda dengan teliti', cancel: 'Batalkan analisis',
  },
  tl: {
    analysisDone: 'Tapos na ang pagsusuri', analyzingLive: 'Sinusuri ang sugnay {done}/{total}', liveHint: 'Unang lalabas ang mga natapos na sugnay',
    verifyingNote: 'Kasalukuyang bine-verify ng AI — mapi-finalize ang resulta pagkatapos',
    headlineTotal: 'Sa kabuuang {total} sugnay,', headlineNeed: '{need} ang kailangang bigyang-pansin',
    danger: 'Panganib', caution: 'Ingat', safe: 'Ligtas',
    checkFirst: 'Suriin muna ito', standardClause: 'Karaniwang sugnay', standardClauseLong: 'Karaniwang sugnay ito', all: 'Lahat',
    copyAllQuestions: 'Kopyahin lahat ng tanong', evidence: 'Batayan', noClauses: 'Walang tumutugmang sugnay', seeDetail: 'Tingnan ang detalye', finish: 'Gamitin ang resulta at tapusin',
    backToSummary: 'Bumalik sa buod', clauseList: 'Mga sugnay', explainSimply: 'Sa simpleng salita', whyCheck: 'Bakit dapat suriin?',
    originalText: 'Orihinal na teksto ng kontrata (Korean)', askOther: 'Itanong sa kabilang partido', askKoreanHint: 'Nasa Korean ang mga tanong — maaaring ipakita ang screen na ito',
    otherClauses: 'Iba pang sugnay', finishDetail: 'Tapos na — gamitin ang resulta',
    progressTitle: 'Maingat na sinusuri ang iyong kontrata', cancel: 'Kanselahin',
  },
  ne: {
    analysisDone: 'विश्लेषण पूरा भयो', analyzingLive: 'धारा {done}/{total} विश्लेषण गर्दै', liveHint: 'सकिएका धाराहरू पहिले देखिन्छन्',
    verifyingNote: 'AI प्रमाणीकरण चलिरहेको छ — सकिएपछि नतिजा पक्का हुन्छ',
    headlineTotal: 'जम्मा {total} धारामध्ये,', headlineNeed: '{need} धारामा ध्यान दिनुपर्छ',
    danger: 'खतरा', caution: 'सावधान', safe: 'सुरक्षित',
    checkFirst: 'पहिले यो जाँच्नुहोस्', standardClause: 'मानक धारा', standardClauseLong: 'यो मानक धारा हो', all: 'सबै',
    copyAllQuestions: 'सबै प्रश्न कपी गर्नुहोस्', evidence: 'आधार', noClauses: 'मिल्ने धारा छैन', seeDetail: 'विवरण हेर्नुहोस्', finish: 'नतिजा प्रयोग गरी सक्नुहोस्',
    backToSummary: 'सारांशमा फर्कनुहोस्', clauseList: 'धारा सूची', explainSimply: 'सजिलो भाषामा', whyCheck: 'किन जाँच्नुपर्छ?',
    originalText: 'सम्झौताको मूल पाठ (कोरियाली)', askOther: 'अर्को पक्षलाई सोध्नुहोस्', askKoreanHint: 'प्रश्नहरू कोरियालीमा छन् — यो स्क्रिन सिधै देखाउन सक्नुहुन्छ',
    otherClauses: 'अन्य धाराहरू', finishDetail: 'सकियो — नतिजा प्रयोग गर्नुहोस्',
    progressTitle: 'तपाईंको सम्झौता ध्यानपूर्वक जाँच्दै', cancel: 'रद्द गर्नुहोस्',
  },
  km: {
    analysisDone: 'ការវិភាគបានបញ្ចប់', analyzingLive: 'កំពុងវិភាគប្រការ {done}/{total}', liveHint: 'ប្រការដែលរួចរាល់នឹងបង្ហាញមុន',
    verifyingNote: 'AI កំពុងផ្ទៀងផ្ទាត់ — លទ្ធផលនឹងបញ្ជាក់នៅពេលបញ្ចប់',
    headlineTotal: 'ក្នុងចំណោមប្រការ {total} ទាំងអស់,', headlineNeed: 'មាន {need} ដែលត្រូវប្រុងប្រយ័ត្ន',
    danger: 'គ្រោះថ្នាក់', caution: 'ប្រយ័ត្ន', safe: 'សុវត្ថិភាព',
    checkFirst: 'សូមពិនិត្យប្រការនេះមុន', standardClause: 'ប្រការស្តង់ដារ', standardClauseLong: 'នេះជាប្រការស្តង់ដារ', all: 'ទាំងអស់',
    copyAllQuestions: 'ចម្លងសំណួរទាំងអស់', evidence: 'ភស្តុតាង', noClauses: 'គ្មានប្រការត្រូវគ្នា', seeDetail: 'មើលលម្អិត', finish: 'ប្រើលទ្ធផល ហើយបញ្ចប់',
    backToSummary: 'ត្រឡប់ទៅសង្ខេប', clauseList: 'បញ្ជីប្រការ', explainSimply: 'និយាយឱ្យងាយយល់', whyCheck: 'ហេតុអ្វីត្រូវពិនិត្យ?',
    originalText: 'អត្ថបទកិច្ចសន្យាដើម (ភាសាកូរ៉េ)', askOther: 'សួរភាគីម្ខាងទៀត', askKoreanHint: 'សំណួរជាភាសាកូរ៉េ — អាចបង្ហាញអេក្រង់នេះដោយផ្ទាល់',
    otherClauses: 'ប្រការផ្សេងទៀត', finishDetail: 'រួចរាល់ — ប្រើលទ្ធផល',
    progressTitle: 'កំពុងពិនិត្យកិច្ចសន្យារបស់អ្នកយ៉ាងម៉ត់ចត់', cancel: 'បោះបង់',
  },
  my: {
    analysisDone: 'စိစစ်မှု ပြီးပါပြီ', analyzingLive: 'အပိုဒ် {done}/{total} စိစစ်နေသည်', liveHint: 'ပြီးသောအပိုဒ်များ အရင်ပြသမည်',
    verifyingNote: 'AI စိစစ်အတည်ပြုနေသည် — ပြီးမှ ရလဒ်အတည်ဖြစ်မည်',
    headlineTotal: 'စုစုပေါင်း အပိုဒ် {total} ခုအနက်,', headlineNeed: '{need} ခုကို သတိပြုရန်လိုသည်',
    danger: 'အန္တရာယ်', caution: 'သတိ', safe: 'စိတ်ချရ',
    checkFirst: 'ဤအပိုဒ်ကို အရင်စစ်ပါ', standardClause: 'စံအပိုဒ်', standardClauseLong: 'ဤသည် စံအပိုဒ်ဖြစ်သည်', all: 'အားလုံး',
    copyAllQuestions: 'မေးခွန်းအားလုံး ကူးယူရန်', evidence: 'အထောက်အထား', noClauses: 'ကိုက်ညီသောအပိုဒ် မရှိပါ', seeDetail: 'အသေးစိတ်ကြည့်ရန်', finish: 'ရလဒ်သုံးပြီး ပြီးဆုံးရန်',
    backToSummary: 'အနှစ်ချုပ်သို့ ပြန်သွားရန်', clauseList: 'အပိုဒ်စာရင်း', explainSimply: 'ရိုးရှင်းစွာပြောရလျှင်', whyCheck: 'ဘာကြောင့်စစ်သင့်သလဲ?',
    originalText: 'စာချုပ်မူရင်း (ကိုရီးယားဘာသာ)', askOther: 'တစ်ဖက်လူကို မေးပါ', askKoreanHint: 'မေးခွန်းများသည် ကိုရီးယားဘာသာဖြစ်သည် — ဤမျက်နှာပြင်ကို တိုက်ရိုက်ပြနိုင်သည်',
    otherClauses: 'အခြားအပိုဒ်များ', finishDetail: 'ပြီးပါပြီ — ရလဒ်ကိုသုံးပါ',
    progressTitle: 'သင့်စာချုပ်ကို သေချာစွာ စစ်ဆေးနေသည်', cancel: 'ပယ်ဖျက်ရန်',
  },
  mn: {
    analysisDone: 'Шинжилгээ дууслаа', analyzingLive: 'Заалт {done}/{total}-г шинжилж байна', liveHint: 'Дууссан заалтууд эхэлж харагдана',
    verifyingNote: 'AI баталгаажуулалт явагдаж байна — дууссаны дараа үр дүн батлагдана',
    headlineTotal: 'Нийт {total} заалтаас,', headlineNeed: '{need} заалтад анхаарал хэрэгтэй',
    danger: 'Аюултай', caution: 'Болгоомжтой', safe: 'Аюулгүй',
    checkFirst: 'Эхлээд үүнийг шалгана уу', standardClause: 'Стандарт заалт', standardClauseLong: 'Энэ бол стандарт заалт', all: 'Бүгд',
    copyAllQuestions: 'Бүх асуултыг хуулах', evidence: 'Үндэслэл', noClauses: 'Тохирох заалт алга', seeDetail: 'Дэлгэрэнгүй үзэх', finish: 'Үр дүнг ашиглаад дуусгах',
    backToSummary: 'Товчлол руу буцах', clauseList: 'Заалтын жагсаалт', explainSimply: 'Энгийнээр хэлбэл', whyCheck: 'Яагаад шалгах ёстой вэ?',
    originalText: 'Гэрээний эх бичвэр (солонгос хэл)', askOther: 'Нөгөө талаас асуугаарай', askKoreanHint: 'Асуултууд солонгосоор байгаа — энэ дэлгэцийг шууд үзүүлж болно',
    otherClauses: 'Бусад заалт', finishDetail: 'Дууслаа — үр дүнг ашиглах',
    progressTitle: 'Таны гэрээг нягт нямбай шалгаж байна', cancel: 'Цуцлах',
  },
  uz: {
    analysisDone: 'Tahlil yakunlandi', analyzingLive: '{done}/{total}-band tahlil qilinmoqda', liveHint: 'Tugagan bandlar birinchi ko‘rinadi',
    verifyingNote: 'AI tekshiruvi davom etmoqda — tugagach natija tasdiqlanadi',
    headlineTotal: 'Jami {total} banddan,', headlineNeed: '{need} tasiga e’tibor kerak',
    danger: 'Xavfli', caution: 'Ehtiyot', safe: 'Xavfsiz',
    checkFirst: 'Avval shuni tekshiring', standardClause: 'Standart band', standardClauseLong: 'Bu standart band', all: 'Hammasi',
    copyAllQuestions: 'Barcha savollarni nusxalash', evidence: 'Asos', noClauses: 'Mos band topilmadi', seeDetail: 'Batafsil ko‘rish', finish: 'Natijadan foydalanib yakunlash',
    backToSummary: 'Xulosaga qaytish', clauseList: 'Bandlar ro‘yxati', explainSimply: 'Sodda qilib aytganda', whyCheck: 'Nega tekshirish kerak?',
    originalText: 'Shartnoma asl matni (koreys tilida)', askOther: 'Ikkinchi tomondan so‘rang', askKoreanHint: 'Savollar koreys tilida — bu ekranni to‘g‘ridan-to‘g‘ri ko‘rsatishingiz mumkin',
    otherClauses: 'Boshqa bandlar', finishDetail: 'Tayyor — natijadan foydalaning',
    progressTitle: 'Shartnomangiz sinchiklab tekshirilmoqda', cancel: 'Bekor qilish',
  },
  si: {
    analysisDone: 'විශ්ලේෂණය අවසන්', analyzingLive: 'වගන්තිය {done}/{total} විශ්ලේෂණය වෙමින්', liveHint: 'අවසන් වූ වගන්ති මුලින් පෙන්වයි',
    verifyingNote: 'AI සත්‍යාපනය සිදුවෙමින් — අවසන් වූ පසු ප්‍රතිඵල තහවුරු වේ',
    headlineTotal: 'මුළු වගන්ති {total}න්,', headlineNeed: '{need}ක් අවධානය යොමු කළ යුතුයි',
    danger: 'අවදානම්', caution: 'ප්‍රවේශම්', safe: 'ආරක්ෂිත',
    checkFirst: 'මුලින්ම මෙය පරීක්ෂා කරන්න', standardClause: 'සම්මත වගන්තිය', standardClauseLong: 'මෙය සම්මත වගන්තියකි', all: 'සියල්ල',
    copyAllQuestions: 'සියලු ප්‍රශ්න පිටපත් කරන්න', evidence: 'පදනම', noClauses: 'ගැලපෙන වගන්ති නැත', seeDetail: 'විස්තර බලන්න', finish: 'ප්‍රතිඵල භාවිතා කර අවසන් කරන්න',
    backToSummary: 'සාරාංශයට ආපසු', clauseList: 'වගන්ති ලැයිස්තුව', explainSimply: 'සරලව කිවහොත්', whyCheck: 'ඇයි පරීක්ෂා කළ යුත්තේ?',
    originalText: 'ගිවිසුමේ මුල් පිටපත (කොරියානු)', askOther: 'අනෙක් පාර්ශ්වයෙන් අසන්න', askKoreanHint: 'ප්‍රශ්න කොරියානු භාෂාවෙන් — මෙම තිරය කෙලින්ම පෙන්විය හැක',
    otherClauses: 'වෙනත් වගන්ති', finishDetail: 'අවසන් — ප්‍රතිඵල භාවිතා කරන්න',
    progressTitle: 'ඔබේ ගිවිසුම හොඳින් පරීක්ෂා කරමින්', cancel: 'අවලංගු කරන්න',
  },
  bn: {
    analysisDone: 'বিশ্লেষণ সম্পন্ন', analyzingLive: 'ধারা {done}/{total} বিশ্লেষণ চলছে', liveHint: 'সম্পন্ন ধারাগুলো আগে দেখাবে',
    verifyingNote: 'AI যাচাই চলছে — শেষ হলে ফলাফল চূড়ান্ত হবে',
    headlineTotal: 'মোট {total}টি ধারার মধ্যে,', headlineNeed: '{need}টিতে মনোযোগ প্রয়োজন',
    danger: 'ঝুঁকি', caution: 'সতর্ক', safe: 'নিরাপদ',
    checkFirst: 'আগে এটি দেখুন', standardClause: 'প্রমিত ধারা', standardClauseLong: 'এটি একটি প্রমিত ধারা', all: 'সব',
    copyAllQuestions: 'সব প্রশ্ন কপি করুন', evidence: 'ভিত্তি', noClauses: 'মিলে যাওয়া ধারা নেই', seeDetail: 'বিস্তারিত দেখুন', finish: 'ফলাফল ব্যবহার করে শেষ করুন',
    backToSummary: 'সারাংশে ফিরুন', clauseList: 'ধারার তালিকা', explainSimply: 'সহজ ভাষায়', whyCheck: 'কেন দেখা দরকার?',
    originalText: 'চুক্তির মূল পাঠ (কোরীয়)', askOther: 'অপর পক্ষকে জিজ্ঞাসা করুন', askKoreanHint: 'প্রশ্নগুলো কোরীয় ভাষায় — এই স্ক্রিন সরাসরি দেখাতে পারেন',
    otherClauses: 'অন্যান্য ধারা', finishDetail: 'শেষ — ফলাফল ব্যবহার করুন',
    progressTitle: 'আপনার চুক্তি মনোযোগ দিয়ে দেখা হচ্ছে', cancel: 'বাতিল করুন',
  },
  ru: {
    analysisDone: 'Анализ завершён', analyzingLive: 'Анализ пункта {done}/{total}', liveHint: 'Готовые пункты появляются первыми',
    verifyingNote: 'Идёт проверка ИИ — результат будет подтверждён после завершения',
    headlineTotal: 'Из {total} пунктов', headlineNeed: '{need} требуют вашего внимания',
    danger: 'Опасно', caution: 'Внимание', safe: 'Безопасно',
    checkFirst: 'Проверьте это в первую очередь', standardClause: 'Стандартный пункт', standardClauseLong: 'Это стандартный пункт', all: 'Все',
    copyAllQuestions: 'Скопировать все вопросы', evidence: 'Основание', noClauses: 'Нет подходящих пунктов', seeDetail: 'Подробнее', finish: 'Использовать результаты и завершить',
    backToSummary: 'К сводке', clauseList: 'Список пунктов', explainSimply: 'Простыми словами', whyCheck: 'Почему это важно?',
    originalText: 'Оригинальный текст договора (корейский)', askOther: 'Спросите другую сторону', askKoreanHint: 'Вопросы на корейском — можно показать этот экран напрямую',
    otherClauses: 'Другие пункты', finishDetail: 'Готово — использовать результаты',
    progressTitle: 'Внимательно проверяем ваш договор', cancel: 'Отменить',
  },
  ja: {
    analysisDone: '分析完了', analyzingLive: '条項 {done}/{total} を分析中', liveHint: '完了した条項から先に表示されます',
    verifyingNote: 'AI検証が進行中です — 完了すると結果が確定します',
    headlineTotal: '全{total}条項のうち、', headlineNeed: '{need}件に注意が必要です',
    danger: '危険', caution: '注意', safe: '安全',
    checkFirst: 'まずこれを確認', standardClause: '標準条項', standardClauseLong: 'これは標準的な条項です', all: 'すべて',
    copyAllQuestions: '質問を全てコピー', evidence: '根拠', noClauses: '該当する条項はありません', seeDetail: '詳しく見る', finish: '結果を活用して終了',
    backToSummary: '要約に戻る', clauseList: '条項リスト', explainSimply: '簡単に言うと', whyCheck: 'なぜ確認が必要？',
    originalText: '契約書原文（韓国語）', askOther: '相手方に質問しましょう', askKoreanHint: '質問は韓国語です — この画面をそのまま見せても構いません',
    otherClauses: '他の条項を見る', finishDetail: '確認を終えて結果を活用',
    progressTitle: '契約書を丁寧に確認しています', cancel: '分析をキャンセル',
  },
}

/** 위험 유형 10종 번역 — 키는 에이전트가 반환하는 한국어 원문. */
const RISK_TYPES: Record<LangCode, Record<string, string>> = {
  ko: {},
  en: {
    '과도한 위약금': 'Excessive penalty', '일방적 계약 해지': 'One-sided termination', '보증금 반환 지연': 'Delayed deposit refund',
    '책임 면제': 'Liability waiver', '불명확한 수수료·이자 조건': 'Unclear fees/interest', '신탁관계·소유권 불안정 고지': 'Trust/ownership instability',
    '부당한 비용·세금 전가': 'Unfair cost/tax shifting', '일방적 급부·조건 변경': 'One-sided term changes', '선택권 제한·구입 강제': 'Forced purchase/limited choice',
    '권리행사 제한': 'Restriction of rights',
  },
  zh: {
    '과도한 위약금': '过高违约金', '일방적 계약 해지': '单方解除合同', '보증금 반환 지연': '押金返还延迟',
    '책임 면제': '免除责任', '불명확한 수수료·이자 조건': '手续费/利息不明确', '신탁관계·소유권 불안정 고지': '信托/所有权不稳定',
    '부당한 비용·세금 전가': '不当转嫁费用/税金', '일방적 급부·조건 변경': '单方变更条件', '선택권 제한·구입 강제': '强制购买/限制选择',
    '권리행사 제한': '限制行使权利',
  },
  vi: {
    '과도한 위약금': 'Phạt vi phạm quá mức', '일방적 계약 해지': 'Đơn phương chấm dứt hợp đồng', '보증금 반환 지연': 'Chậm hoàn trả tiền đặt cọc',
    '책임 면제': 'Miễn trừ trách nhiệm', '불명확한 수수료·이자 조건': 'Phí/lãi suất không rõ ràng', '신탁관계·소유권 불안정 고지': 'Quyền sở hữu/ủy thác bất ổn',
    '부당한 비용·세금 전가': 'Đẩy chi phí/thuế bất hợp lý', '일방적 급부·조건 변경': 'Đơn phương thay đổi điều kiện', '선택권 제한·구입 강제': 'Ép mua/hạn chế lựa chọn',
    '권리행사 제한': 'Hạn chế quyền lợi',
  },
  th: {
    '과도한 위약금': 'ค่าปรับสูงเกินไป', '일방적 계약 해지': 'บอกเลิกสัญญาฝ่ายเดียว', '보증금 반환 지연': 'คืนเงินมัดจำล่าช้า',
    '책임 면제': 'ยกเว้นความรับผิด', '불명확한 수수료·이자 조건': 'ค่าธรรมเนียม/ดอกเบี้ยไม่ชัดเจน', '신탁관계·소유권 불안정 고지': 'กรรมสิทธิ์/ทรัสต์ไม่มั่นคง',
    '부당한 비용·세금 전가': 'ผลักภาระค่าใช้จ่าย/ภาษีอย่างไม่เป็นธรรม', '일방적 급부·조건 변경': 'เปลี่ยนเงื่อนไขฝ่ายเดียว', '선택권 제한·구입 강제': 'บังคับซื้อ/จำกัดทางเลือก',
    '권리행사 제한': 'จำกัดการใช้สิทธิ',
  },
  id: {
    '과도한 위약금': 'Denda berlebihan', '일방적 계약 해지': 'Pemutusan kontrak sepihak', '보증금 반환 지연': 'Pengembalian deposit tertunda',
    '책임 면제': 'Pembebasan tanggung jawab', '불명확한 수수료·이자 조건': 'Biaya/bunga tidak jelas', '신탁관계·소유권 불안정 고지': 'Kepemilikan/trust tidak stabil',
    '부당한 비용·세금 전가': 'Pengalihan biaya/pajak tak wajar', '일방적 급부·조건 변경': 'Perubahan syarat sepihak', '선택권 제한·구입 강제': 'Pembelian paksa/pilihan dibatasi',
    '권리행사 제한': 'Pembatasan hak',
  },
  tl: {
    '과도한 위약금': 'Labis na multa', '일방적 계약 해지': 'Isang-panig na pagwawakas', '보증금 반환 지연': 'Naantalang pagsauli ng deposito',
    '책임 면제': 'Pag-iwas sa pananagutan', '불명확한 수수료·이자 조건': 'Malabong bayarin/interes', '신탁관계·소유권 불안정 고지': 'Hindi tiyak na pagmamay-ari/trust',
    '부당한 비용·세금 전가': 'Di-makatarungang paglilipat ng gastos/buwis', '일방적 급부·조건 변경': 'Isang-panig na pagbabago ng kondisyon', '선택권 제한·구입 강제': 'Sapilitang pagbili/limitadong pagpili',
    '권리행사 제한': 'Paghihigpit sa karapatan',
  },
  ne: {
    '과도한 위약금': 'अत्यधिक जरिवाना', '일방적 계약 해지': 'एकतर्फी सम्झौता अन्त्य', '보증금 반환 지연': 'धरौटी फिर्तामा ढिलाइ',
    '책임 면제': 'जिम्मेवारीबाट उन्मुक्ति', '불명확한 수수료·이자 조건': 'अस्पष्ट शुल्क/ब्याज', '신탁관계·소유권 불안정 고지': 'स्वामित्व/ट्रस्ट अस्थिरता',
    '부당한 비용·세금 전가': 'अनुचित खर्च/कर सार्ने', '일방적 급부·조건 변경': 'एकतर्फी सर्त परिवर्तन', '선택권 제한·구입 강제': 'जबरजस्ती खरिद/छनोट सीमित',
    '권리행사 제한': 'अधिकार प्रयोगमा रोक',
  },
  km: {
    '과도한 위약금': 'ពិន័យលើសកម្រិត', '일방적 계약 해지': 'បញ្ចប់កិច្ចសន្យាតែម្ខាង', '보증금 반환 지연': 'ពន្យារពេលសងប្រាក់កក់',
    '책임 면제': 'រួចផុតពីទំនួលខុសត្រូវ', '불명확한 수수료·이자 조건': 'ថ្លៃសេវា/ការប្រាក់មិនច្បាស់', '신탁관계·소유권 불안정 고지': 'កម្មសិទ្ធិ/ទ្រាស្តមិនច្បាស់លាស់',
    '부당한 비용·세금 전가': 'បង្វែរចំណាយ/ពន្ធដោយអយុត្តិធម៌', '일방적 급부·조건 변경': 'ផ្លាស់ប្តូរលក្ខខណ្ឌតែម្ខាង', '선택권 제한·구입 강제': 'បង្ខំទិញ/កំណត់ជម្រើស',
    '권리행사 제한': 'រឹតបន្តឹងសិទ្ធិ',
  },
  my: {
    '과도한 위약금': 'အလွန်အကျွံ ဒဏ်ကြေး', '일방적 계약 해지': 'တစ်ဖက်သတ် စာချုပ်ဖျက်သိမ်းခြင်း', '보증금 반환 지연': 'အာမခံငွေ ပြန်အမ်းရန် နှောင့်နှေးခြင်း',
    '책임 면제': 'တာဝန်ကင်းလွတ်ခွင့်', '불명확한 수수료·이자 조건': 'မရှင်းလင်းသော ဝန်ဆောင်ခ/အတိုး', '신탁관계·소유권 불안정 고지': 'ပိုင်ဆိုင်မှု/ယုံကြည်အပ်နှံမှု မတည်ငြိမ်ခြင်း',
    '부당한 비용·세금 전가': 'မတရား ကုန်ကျစရိတ်/အခွန် လွှဲချခြင်း', '일방적 급부·조건 변경': 'တစ်ဖက်သတ် စည်းကမ်းပြောင်းလဲခြင်း', '선택권 제한·구입 강제': 'အတင်းဝယ်ခိုင်းခြင်း/ရွေးချယ်ခွင့်ကန့်သတ်ခြင်း',
    '권리행사 제한': 'အခွင့်အရေးကျင့်သုံးမှု ကန့်သတ်ခြင်း',
  },
  mn: {
    '과도한 위약금': 'Хэт өндөр торгууль', '일방적 계약 해지': 'Нэг талын гэрээ цуцлалт', '보증금 반환 지연': 'Барьцаа буцаалт хойшлох',
    '책임 면제': 'Хариуцлагаас чөлөөлөх', '불명확한 수수료·이자 조건': 'Тодорхойгүй шимтгэл/хүү', '신탁관계·소유권 불안정 고지': 'Өмчлөл/итгэлцлийн тогтворгүй байдал',
    '부당한 비용·세금 전가': 'Зардал/татварыг шударга бусаар шилжүүлэх', '일방적 급부·조건 변경': 'Нэг талын нөхцөл өөрчлөлт', '선택권 제한·구입 강제': 'Албадан худалдан авалт/сонголт хязгаарлах',
    '권리행사 제한': 'Эрх эдлэхийг хязгаарлах',
  },
  uz: {
    '과도한 위약금': 'Haddan ortiq jarima', '일방적 계약 해지': 'Bir tomonlama shartnoma bekor qilish', '보증금 반환 지연': 'Garov pulini qaytarishni kechiktirish',
    '책임 면제': 'Javobgarlikdan ozod qilish', '불명확한 수수료·이자 조건': 'Noaniq to‘lov/foiz shartlari', '신탁관계·소유권 불안정 고지': 'Mulk/trast beqarorligi',
    '부당한 비용·세금 전가': 'Xarajat/soliqni nohaq yuklash', '일방적 급부·조건 변경': 'Bir tomonlama shart o‘zgartirish', '선택권 제한·구입 강제': 'Majburiy xarid/tanlov cheklovi',
    '권리행사 제한': 'Huquqlarni cheklash',
  },
  si: {
    '과도한 위약금': 'අධික දඩ මුදල්', '일방적 계약 해지': 'ඒකපාර්ශ්වික ගිවිසුම් අවසන් කිරීම', '보증금 반환 지연': 'තැන්පතු ආපසු දීම ප්‍රමාදය',
    '책임 면제': 'වගකීමෙන් නිදහස් වීම', '불명확한 수수료·이자 조건': 'අපැහැදිලි ගාස්තු/පොලී', '신탁관계·소유권 불안정 고지': 'අයිතිය/භාරය අස්ථාවර',
    '부당한 비용·세금 전가': 'අසාධාරණ වියදම්/බදු පැවරීම', '일방적 급부·조건 변경': 'ඒකපාර්ශ්වික කොන්දේසි වෙනස් කිරීම', '선택권 제한·구입 강제': 'බලහත්කාර මිලදී ගැනීම/තේරීම් සීමා',
    '권리행사 제한': 'අයිතිවාසිකම් සීමා කිරීම',
  },
  bn: {
    '과도한 위약금': 'অতিরিক্ত জরিমানা', '일방적 계약 해지': 'একতরফা চুক্তি বাতিল', '보증금 반환 지연': 'জামানত ফেরতে বিলম্ব',
    '책임 면제': 'দায় থেকে অব্যাহতি', '불명확한 수수료·이자 조건': 'অস্পষ্ট ফি/সুদ', '신탁관계·소유권 불안정 고지': 'মালিকানা/ট্রাস্ট অস্থিতিশীলতা',
    '부당한 비용·세금 전가': 'অন্যায্য খরচ/কর চাপানো', '일방적 급부·조건 변경': 'একতরফা শর্ত পরিবর্তন', '선택권 제한·구입 강제': 'জোরপূর্বক ক্রয়/সীমিত পছন্দ',
    '권리행사 제한': 'অধিকার প্রয়োগে বাধা',
  },
  ru: {
    '과도한 위약금': 'Чрезмерная неустойка', '일방적 계약 해지': 'Одностороннее расторжение', '보증금 반환 지연': 'Задержка возврата депозита',
    '책임 면제': 'Освобождение от ответственности', '불명확한 수수료·이자 조건': 'Неясные комиссии/проценты', '신탁관계·소유권 불안정 고지': 'Нестабильность собственности/траста',
    '부당한 비용·세금 전가': 'Несправедливое перекладывание расходов/налогов', '일방적 급부·조건 변경': 'Одностороннее изменение условий', '선택권 제한·구입 강제': 'Навязанная покупка/ограничение выбора',
    '권리행사 제한': 'Ограничение прав',
  },
  ja: {
    '과도한 위약금': '過大な違約金', '일방적 계약 해지': '一方的な契約解除', '보증금 반환 지연': '保証金返還の遅延',
    '책임 면제': '責任免除', '불명확한 수수료·이자 조건': '不明確な手数料・利息', '신탁관계·소유권 불안정 고지': '信託・所有権の不安定',
    '부당한 비용·세금 전가': '不当な費用・税金の転嫁', '일방적 급부·조건 변경': '一方的な条件変更', '선택권 제한·구입 강제': '購入強制・選択制限',
    '권리행사 제한': '権利行使の制限',
  },
}

export function t(lang: LangCode, key: UIKey, vars?: Record<string, number | string>): string {
  let text = UI[lang]?.[key] ?? UI.en[key] ?? UI.ko[key]
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{${name}}`).join(String(value))
    }
  }
  return text
}

/** 에이전트가 반환한 한국어 risk_type을 화면 언어로 변환. 사전에 없으면 원문 유지. */
export function riskTypeLabel(lang: LangCode, koreanType: string): string {
  if (lang === 'ko') return koreanType
  return RISK_TYPES[lang]?.[koreanType] ?? RISK_TYPES.en[koreanType] ?? koreanType
}

export function riskLevelLabel(lang: LangCode, level: '안전' | '주의' | '위험'): string {
  const key = level === '위험' ? 'danger' : level === '주의' ? 'caution' : 'safe'
  return t(lang, key)
}
