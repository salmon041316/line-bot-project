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
        
        # 🌟 關鍵修改：使用 DATETIME(..., '+8 hours') 轉換為台灣時間
        cursor.execute('''
            SELECT toilet_name, stars, comment, DATETIME(created_at, '+8 hours') AS created_at 
            FROM reviews 
            WHERE toilet_name LIKE ? 
            ORDER BY created_at DESC
        ''', (f'%{keyword}%',))
        
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
        
        # 🌟 關鍵修改：使用 DATETIME(..., '+8 hours') 轉換為台灣時間
        cursor.execute('''
            SELECT toilet_name, stars, comment, DATETIME(created_at, '+8 hours') AS created_at 
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

def search_toilets_from_master(keyword):
    # 從系統的「廁所主資料表」中，模糊搜尋包含關鍵字的廁所名稱
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # 請將 'toilet_info' 和 'name' 替換成妳們資料庫實際的名稱
        cursor.execute('''
            SELECT name AS toilet_name 
            FROM toilets 
            WHERE name LIKE ?
        ''', (f'%{keyword}%',))
        
        rows = cursor.fetchall()
        
        result_list = []
        for row in rows:
            result_list.append({"toilet_name": row["toilet_name"]})
            
        return result_list
        
    except Exception as e:
        print(f"搜尋廁所資料庫失敗: {e}")
        return [] 
        
    finally:
        conn.close()

# --- 管理者後台專用功能 ---

def get_all_reviews_for_admin():
    """撈出系統內所有的評價，供後台列表顯示"""
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 🌟 關鍵修改：後台也一併轉換為台灣時間
        cursor.execute('''
            SELECT id, toilet_name, stars, comment, DATETIME(created_at, '+8 hours') AS created_at 
            FROM reviews 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        result_list = [dict(row) for row in rows]
        return result_list
        
    except Exception as e:
        print(f"撈取後台評價失敗: {e}")
        return []
    finally:
        conn.close()

def delete_review_by_id(review_id):
    """根據評價的 ID 來刪除該筆資料"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # 執行刪除指令
        cursor.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        conn.commit()
        return True
        
    except Exception as e:
        print(f"刪除評價失敗: {e}")
        return False
    finally:
        conn.close()

def add_coupon(vendor_name, coupon_text, target_keyword):
    """新增一張折價券到資料庫"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO coupons (vendor_name, coupon_text, target_keyword) 
            VALUES (?, ?, ?)
        ''', (vendor_name, coupon_text, target_keyword))
        conn.commit()
        return True
    except Exception as e:
        print(f"新增折價券失敗: {e}")
        return False
    finally:
        conn.close()

def get_all_coupons():
    """撈出所有已發布的折價券"""
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM coupons ORDER BY id DESC')
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"撈取折價券失敗: {e}")
        return []
    finally:
        conn.close()

# ==========================================
# 🎁 OMO 商業獎勵機制專區 (UGC 評價獎勵)
# ==========================================

def get_user_review_count(user_id):
    """計算特定使用者目前總共留過幾則評價"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # 用 COUNT(*) 來計算這個 user_id 出現過幾次
        cursor.execute('SELECT COUNT(*) FROM reviews WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        
        return count
        
    except Exception as e:
        print(f"計算評價數量失敗: {e}")
        return 0
    finally:
        conn.close()

def get_random_coupon():
    """隨機抽出一張系統內發布的折價券當作獎勵"""
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 利用 ORDER BY RANDOM() 隨機洗牌，並 LIMIT 1 只抽第一張
        cursor.execute('SELECT * FROM coupons ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
        
    except Exception as e:
        print(f"抽取折價券失敗: {e}")
        return None
    finally:
        conn.close()