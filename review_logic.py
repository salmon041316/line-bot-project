import sqlite3

def save_review_to_db(user_id, toilet_name, stars, comment):
    # 接收從主程式傳來的資料，負責把它寫進 SQLite 資料庫裡的 reviews 表格
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

def get_reviews_by_toilet(keyword):
    # 根據關鍵字，從資料庫模糊搜尋所有相關評價，並依照時間由新到舊排序
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # 1. 關鍵修改：用 LIKE 取代 =，並把 toilet_name 也選出來
        cursor.execute('''
            SELECT toilet_name, stars, comment, created_at 
            FROM reviews 
            WHERE toilet_name LIKE ? 
            ORDER BY created_at DESC
        ''', (f'%{keyword}%',))
        
        rows = cursor.fetchall()
        
        reviews_list = []
        for row in rows:
            reviews_list.append({
                "toilet_name": row["toilet_name"], # 2. 把廁所名稱也打包回傳
                "stars": row["stars"],
                "comment": row["comment"],
                "created_at": row["created_at"]
            })
            
        return reviews_list
        
    except Exception as e:
        print(f"讀取評價失敗: {e}")
        return [] 
        
    finally:
        conn.close()

def get_latest_reviews(limit=10):
    # 不限廁所名稱，直接撈出全站最新建立的幾筆評價 (預設 10 筆)
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # 只要時間最新，通通撈出來
        cursor.execute('''
            SELECT toilet_name, stars, comment, created_at 
            FROM reviews 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        reviews_list = []
        for row in rows:
            reviews_list.append({
                "toilet_name": row["toilet_name"],
                "stars": row["stars"],
                "comment": row["comment"],
                "created_at": row["created_at"]
            })
            
        return reviews_list
        
    except Exception as e:
        print(f"讀取最新評價失敗: {e}")
        return [] 
        
    finally:
        conn.close()