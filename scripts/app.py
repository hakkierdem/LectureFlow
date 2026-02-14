import asyncio
import aiosqlite  
import logging
import os
from dotenv import load_dotenv
from datetime import datetime,timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton,ReplyKeyboardMarkup,KeyboardButton
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram.filters.callback_data import CallbackData
from apscheduler.schedulers.asyncio import AsyncIOScheduler


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(BASE_DIR, "database", "lectureflow.db") #

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

calendar = SimpleCalendar(show_alerts=True)

# --- Basic Functions --- 
async def get_todays_lessons(date_str):

    async with aiosqlite.connect(database_path) as db:
        
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT lesson_id,lecture_name,time FROM lessons WHERE date = ?",(date_str,)
        ) as cursor:
            return await cursor.fetchall()
        
async def save_attendance(user_id,lesson_id,status):

    async with aiosqlite.connect(database_path) as db:

        await db.execute(
            "INSERT OR REPLACE INTO attendance (user_id, lesson_id, status) VALUES (?, ?, ?)",(user_id,lesson_id,status)
        )

        await db.commit()

# --- Basis Functions ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, message.from_user.username)
        )
        await db.commit()

    
    kb = [
        [KeyboardButton(text="📅 Bugünün Programı"), KeyboardButton(text="🔮 Yarınki Program")],
        [KeyboardButton(text="📝 Bugünün Yoklaması"), KeyboardButton(text="📅 Tarih Seç (Yoklama)")],
        [KeyboardButton(text="📊 Genel Profilim"),KeyboardButton(text = "📉 Kalan Devamsızlık Hakkı")],
        [KeyboardButton(text = "ℹ️ Yardım & İpucu")]
    ]
    
    main_menu = ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True, 
        input_field_placeholder="Bir işlem seçin..."
    )


    
    welcome_text = (
        f"👋 <b>Merhaba {user_name}!</b>\n\n"
        f"<b>LectureFlow </b> akademik asistanına hoş geldin. 🚀\n"
        f"Senin için derslerini takip ediyor ve devamsızlık sınırlarını denetliyorum.\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"👇 <b>Neler Yapabilirsin?</b>\n"
        f"• Programını anlık kontrol edebilir,\n"
        f"• Kalan yoklama haklarını görebilir,\n"
        f"• Geçmişe dönük yoklama girebilirsin.\n"
        f"━━━━━━━━━━━━━━\n"
        f"<i>Keyifli bir dönem dilerim!</i> ✨"
    )

    await message.answer(welcome_text, reply_markup=main_menu, parse_mode="HTML")



@dp.message(F.text == "📅 Bugünün Programı")
async def btn_today(message: types.Message):
    await cmd_program_daily(message) 

@dp.message(F.text == "🔮 Yarınki Program")
async def btn_tomorrow(message: types.Message):
    await cmd_program_daily(message)

@dp.message(F.text == "📊 Genel Profilim")
async def btn_profile(message: types.Message):
    await cmd_profil(message)

@dp.message(F.text == "📝 Bugünün Yoklaması")
async def handle_yoklama_bugun(message: types.Message):
    await cmd_today(message) 


@dp.message(F.text == "📅 Tarih Seç (Yoklama)")
async def handle_yoklama_tarih(message: types.Message):
    await yoklama_tarih(message)

@dp.message(F.text == "📉 Kalan Devamsızlık Hakkı")
async def kalan_devamsizlik_hakki(message : types.Message):
    await cmd_yoklama(message)

@dp.message(F.text == "ℹ️ Yardım & İpucu")
async def btn_help(message: types.Message):
    help_text = (
        "💡 <b>Küçük Bir İpucu:</b>\n\n"
        "Her akşam saat <b>18:30</b>'da sana o günün yoklamasını girmen için hatırlatma yapacağım.\n\n"
        "Eğer <b>23:00</b>'a kadar eksik girişin kalırsa seni tekrar uyaracağım. 😉"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("yoklama_bugun"))
async def cmd_today(message: types.Message):
    
    today = datetime.now().strftime('%Y-%m-%d')
    lessons = await get_todays_lessons(today)
    
    if not lessons:
        await message.answer("Bugün programında ders görünmüyor. Dinlenmene bak! ☕")
        return

    await message.answer("🗓 Bugünün dersleri aşağıda. Durumlarını işaretle:")

    for row in lessons:
        
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(text="✅ Girdim", callback_data=f"att_{row['lesson_id']}_1"))
        builder.add(InlineKeyboardButton(text="❌ Girmedim", callback_data=f"att_{row['lesson_id']}_0"))
        
        await message.answer(
            f"📍 {row['time']} - {row['lecture_name']}",
            reply_markup=builder.as_markup()
        )



@dp.callback_query(F.data.startswith("att_"))
async def handle_attendance_button(callback: types.CallbackQuery):
    
    data_parts = callback.data.split("_")
    lesson_id = int(data_parts[1])
    status = int(data_parts[2])

    
    await save_attendance(callback.from_user.id, lesson_id, status)
    
    
    sonuc = "✅ GİRDİN" if status == 1 else "❌ GİRMEDİN"
    
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\nKayıt: {sonuc}"
    )
    
    await callback.answer("Yoklama başarıyla işlendi.")


@dp.message(Command("yoklama_tarih"))
async def yoklama_tarih(message: types.Message):

    await message.answer(
        "📅 **Lütfen yoklamasını doldurmak istediğiniz tarihi seçin:**",
        reply_markup=await SimpleCalendar().start_calendar(),
        parse_mode="Markdown"
    )



@dp.callback_query(SimpleCalendarCallback.filter())
async def process_simple_calendar(callback_query: types.CallbackQuery, callback_data: CallbackData):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    
    if selected:
        formatted_date = date.strftime("%Y-%m-%d")
        
        async with aiosqlite.connect(database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM lessons WHERE date = ?", (formatted_date,)
            ) as cursor:
                lessons = await cursor.fetchall()

        if not lessons:
            await callback_query.message.answer(f"ℹ️ `{formatted_date}` tarihinde herhangi bir ders bulunamadı.")
            return

        await callback_query.message.answer(
            f"✅ `{formatted_date}` tarihi seçildi.\nŞimdi dersleri işaretleyebilirsiniz:",
            parse_mode="Markdown"
        )
        

        for lesson in lessons:
            builder = InlineKeyboardBuilder()
            
            builder.add(
                InlineKeyboardButton(text="✅ Geldim", callback_data=f"att_{lesson['lesson_id']}_1"),
                InlineKeyboardButton(text="❌ Gelmedim", callback_data=f"att_{lesson['lesson_id']}_0")
            )
            builder.adjust(2)
            
            await callback_query.message.answer(
                f"📍 {lesson['time']} - {lesson['lecture_name']}",
            reply_markup=builder.as_markup()
            )


@dp.message(Command("kalan_hak"))
async def cmd_yoklama(message: types.Message):
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="4. Komite", callback_data="sel_comm_4"))
    builder.add(InlineKeyboardButton(text="5. Komite", callback_data="sel_comm_5"))
    
    builder.add(InlineKeyboardButton(text="Genel Dersler (Dönemlik)", callback_data="sel_comm_none"))
    
    builder.adjust(1) 
    await message.answer("Hangi grubun yoklamasına bakmak istersin?", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("sel_comm_"))
async def process_committee_select(callback: types.CallbackQuery):
    committee_id = callback.data.split("_")[-1]
    
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        
        
        if committee_id == "none":
            query = """
                SELECT lecture_name, type FROM lessons 
                WHERE committee IS NULL 
                GROUP BY lecture_name, type 
                HAVING COUNT(*) > 0
            """
            params = ()
        else:
            query = """
                SELECT lecture_name, type FROM lessons 
                WHERE committee = ? 
                GROUP BY lecture_name, type 
                HAVING COUNT(*) > 0
            """
            params = (committee_id,)
        
        async with db.execute(query, params) as cursor:
            lessons = await cursor.fetchall()

    if not lessons:
        await callback.answer("Bu grupta aktif ders bulunamadı.")
        return

    builder = InlineKeyboardBuilder()
    for row in lessons:
        lecture_short = row['lecture_name'][:20]
        
        l_type = row['type'][0]
        builder.add(InlineKeyboardButton(
            text=f"{row['lecture_name']}", 
            callback_data=f"calc_{committee_id}_{lecture_short}_{l_type}")
        )
    
    builder.adjust(1)
    await callback.message.edit_text(
        f"📂 *Kategori:* `{'Genel Dersler' if committee_id == 'none' else f'{committee_id}. Komite'}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"Lütfen analiz edilecek dersi seçin:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("calc_"))
async def process_calculation(callback: types.CallbackQuery):
    _, committee_id, lecture_prefix, l_type = callback.data.split("_")
    user_id = callback.from_user.id

    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        
        
        if committee_id == "none":
            total_sql = "SELECT COUNT(*) as total FROM lessons WHERE committee IS NULL AND lecture_name LIKE ?"
            total_params = (f"{lecture_prefix}%",)
            
            missed_sql = """
                SELECT COUNT(*) as missed FROM attendance a
                JOIN lessons l ON a.lesson_id = l.lesson_id
                WHERE a.user_id = ? AND l.committee IS NULL AND l.lecture_name LIKE ? AND a.status = 0
            """
            missed_params = (user_id, f"{lecture_prefix}%")
        else:
            total_sql = "SELECT COUNT(*) as total FROM lessons WHERE committee = ? AND lecture_name LIKE ?"
            total_params = (committee_id, f"{lecture_prefix}%")
            
            missed_sql = """
                SELECT COUNT(*) as missed FROM attendance a
                JOIN lessons l ON a.lesson_id = l.lesson_id
                WHERE a.user_id = ? AND l.committee = ? AND l.lecture_name LIKE ? AND a.status = 0
            """
            missed_params = (user_id, committee_id, f"{lecture_prefix}%")

        async with db.execute(total_sql, total_params) as cursor:
            total_row = await cursor.fetchone()
            total_hours = total_row['total'] if total_row else 0

        async with db.execute(missed_sql, missed_params) as cursor:
            missed_row = await cursor.fetchone()
            missed_hours = missed_row['missed'] if missed_row else 0

    
    limit = 0.30 if l_type == "T" else 0.20
    max_absent = int(total_hours * limit)
    remaining = max_absent - missed_hours


    progress_bar = create_progress_bar(missed_hours,max_absent)
    result_text = (
        f"📖 *{lecture_prefix.upper()}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎯 *Kalan Hak:* {remaining} Saat\n"
        f"📉 *Yaptığın Devamsızlık*: {missed_hours} Saat\n"
        f"━━━━━━━━━━━━━━\n"
    )
    

    await callback.message.answer(result_text, parse_mode="Markdown")
    await callback.answer()



def create_progress_bar(attended, total):
    if total == 0: return "⬜" * 10
    
    
    ratio = attended / total
    filled = int(ratio * 10)
    
    
    bar = "🟩" * filled + "🟥" * (10 - filled)
    return bar


@dp.message(Command("profil"))
async def cmd_profil(message: types.Message):
    user_id = message.from_user.id
    current_date = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        
       
        query = """
            SELECT 
                l.lecture_name,
                COUNT(l.lesson_id) as total_occurred,
                SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) as attended_count
            FROM lessons l
            LEFT JOIN attendance a ON l.lesson_id = a.lesson_id AND a.user_id = ?
            WHERE l.date <= ?
            GROUP BY l.lecture_name
            HAVING total_occurred > 0
            ORDER BY l.lecture_name ASC
        """
        
        async with db.execute(query, (user_id, current_date)) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("ℹ️ Henüz işlenmiş bir ders kaydı veya girilmiş bir yoklama bulunamadı.")
        return

    
    report_header = (
        f"👤 *ÖĞRENCİ AKADEMİK PROFİLİ*\n"
        f"📅 Tarih: {current_date}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    report_body = ""
    for row in rows:
        lecture = row['lecture_name']
        attended = row['attended_count'] if row['attended_count'] else 0
        total = row['total_occurred']
        
        percentage = (attended / total) * 100
        bar = create_progress_bar(attended, total)
        
        
        warning = "⚠️" if percentage < 75 else "✅"
        
        report_body += (
            f"{warning} *{lecture}*\n"
            f"`{bar}`  %{percentage:.1f}\n"
            f"└ *Katılım:* {attended}/{total} saat\n\n"
        )

    footer = "━━━━━━━━━━━━━━━━━━━━\n*Not: Sadece tarihi geçen dersler hesaplamaya dahil edilmiştir.*"
    
    await message.answer(report_header + report_body + footer, parse_mode="Markdown")


async def broadcast_reminder(bot: Bot):
    today_str = datetime.now().strftime("%Y-%m-%d")

    todays_lessons = await get_todays_lessons(today_str)
    
    if not todays_lessons:
        return
    
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            
            for row in rows:
                try:
                    await bot.send_message(
                        row['user_id'], 
                        "⏰ Yoklama Saati: Bugünün derslerini girmeyi unutma!"
                    )
                except Exception as e:
                    print(f"Hata: {row['user_id']} id'li kullanıcıya ulaşılamadı. {e}")


async def check_missing_attendance(bot: Bot):
    today = datetime.now().strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        
        
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()

        for user in users:
            uid = user['user_id']
            
            
            query = """
                SELECT 
                    (SELECT COUNT(*) FROM lessons WHERE date = ?) as total,
                    (SELECT COUNT(*) FROM attendance a 
                     JOIN lessons l ON a.lesson_id = l.lesson_id 
                     WHERE l.date = ? AND a.user_id = ?) as filled
            """
            async with db.execute(query, (today, today, uid)) as cursor:
                res = await cursor.fetchone()
                
                
                if res and res['total'] > 0 and res['filled'] < res['total']:
                    await bot.send_message(
                        uid,
                        f"🚨 SON UYARI!\n\nBugün girmeyi unuttuğun `{res['total'] - res['filled']}` ders saati görünüyor.\n"
                        "Veri kaybı yaşamamak için lütfen şimdi doldur! ⏳",
                        parse_mode="Markdown"
                    )


@dp.message(Command("program_bugun"))
@dp.message(Command("program_yarin"))
async def cmd_program_daily(message: types.Message):
    
    is_tomorrow = "yarin" in message.text.lower()
    target_date = datetime.now()
    
    if is_tomorrow:
        target_date += timedelta(days=1)
        label = "YARINKİ"
    else:
        label = "BUGÜNKÜ"
        
    date_str = target_date.strftime("%Y-%m-%d")

    
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT lecture_name, time FROM lessons WHERE date = ? ORDER BY time ASC", 
            (date_str,)
        ) as cursor:
            lessons = await cursor.fetchall()

    
    if not lessons:
        await message.answer(
            f"☕ <b>{label} PROGRAM</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"Bu tarihte herhangi bir ders görünmüyor. Dinlenebilirsin! 🎉",
            parse_mode="HTML"
        )
        return

    
    response = (
        f"📅 <b>{label} DERS PROGRAMI</b>\n"
        f"({date_str})\n"
        f"━━━━━━━━━━━━━━\n"
    )

    
    for l in lessons:
        
        icon = "🧪" if "(P)" in l['lecture_name'].upper() else "📖"
        response += f"⏰ {l['time']}| {icon} <b>{l['lecture_name']}</b>\n"

    response += "━━━━━━━━━━━━━━\n📍 <i>İyi dersler dilerim!</i>"
    
    await message.answer(response, parse_mode="HTML")


async def main():
    

    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

    scheduler.add_job(broadcast_reminder, "cron", hour=18, minute=30, args=[bot])

    scheduler.add_job(check_missing_attendance, "cron", hour=23, minute=00, args=[bot])
    
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot kapatıldı.")