import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def setup_database(csv_file = "data/clean_data.csv",db_name = "lectureflow.db"):

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(f"{db_name} kurulumu başlıyor")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            committee INTEGER,
            lecture_name TEXT,
            type TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, -- Telegram ID
            username TEXT,
            current_committee INTEGER
        )
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lesson_id INTEGER,
            status INTEGER DEFAULT 0,
            UNIQUE(user_id, lesson_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (lesson_id) REFERENCES lessons (lesson_id)
        )
    ''')

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)

        df.columns = ['date', 'time', 'committee', 'lecture_name', 'type']

        df.to_sql('lessons', conn, if_exists='append', index=False)
        print(f"{len(df)} ders oturumu 'lessons' tablosuna başarıyla aktarıldı.")

    else:
        print(f"Hata: {csv_file} bulunamadı!")

    conn.commit()
    conn.close()
    print("Kurulum başarıyla tamamlandı")

if __name__ == "__main__":
    setup_database()

    
    
