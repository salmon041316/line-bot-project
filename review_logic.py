import sqlite3

def save_review_to_db(user_id, toilet_name, stars, comment):
    """
    接收從主程式傳來的資料，負責把它寫進 SQLite 資料庫裡的 reviews 表格
    """
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # 每次寫入前先確認表格存在，如果沒有就立刻建一個
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                toilet_name TEXT NOT NULL,
                stars INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 執行 SQL 新增語法
        cursor.execute('''
            INSERT INTO reviews (user_id, toilet_name, stars, comment)
            VALUES (?, ?, ?, ?)
        ''', (user_id, toilet_name, stars, comment))
        
        conn.commit()
        return True  
        
    except Exception as e:
        print(f"評價寫入失敗: {e}")
        return False 
        
    finally:
        conn.close()