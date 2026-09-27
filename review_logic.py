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

def get_reviews_by_toilet(toilet_name): 

    # 根據廁所名稱，從資料庫撈出所有評價，並依照時間由新到舊排序
    try:
        conn = sqlite3.connect('bot_data.db')
        # 這行用字典的方式 (像 row['stars']) 來讀取資料
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # 執行 SQL 查詢：選取星等、留言、時間，條件是廁所名稱，並用時間倒序排列 (DESC)
        cursor.execute('''
            SELECT stars, comment, created_at 
            FROM reviews 
            WHERE toilet_name = ? 
            ORDER BY created_at DESC
        ''', (toilet_name,))
        
        rows = cursor.fetchall()
        
        # 把撈出來的資料打包成一個乾淨的 List
        reviews_list = []
        for row in rows:
            reviews_list.append({
                "stars": row["stars"],
                "comment": row["comment"],
                "created_at": row["created_at"]
            })
            
        return reviews_list
        
    except Exception as e:
        print(f"讀取評價失敗: {e}")
        return [] # 如果發生錯誤，就回傳空陣列
        
    finally:
        conn.close()