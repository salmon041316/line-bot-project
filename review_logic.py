import sqlite3

def save_review_to_db(user_id, toilet_name, stars, comment):
    """
    接收從主程式傳來的資料，負責把它寫進 SQLite 資料庫裡的 reviews 表格
    """
    try:
        # 連線到妳現有的資料庫
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # 執行 SQL 新增語法
        cursor.execute('''
            INSERT INTO reviews (user_id, toilet_name, stars, comment)
            VALUES (?, ?, ?, ?)
        ''', (user_id, toilet_name, stars, comment))
        
        conn.commit()
        return True  # 寫入成功就回傳 True
        
    except Exception as e:
        print(f"評價寫入失敗: {e}")
        return False # 寫入發生錯誤就回傳 False
        
    finally:
        # 確保無論成功失敗，資料庫都會關閉連線
        conn.close()