import sqlite3
import string
import random

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
        
        # 關鍵修改：使用 DATETIME(..., '+8 hours') 轉換為台灣時間
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

def check_user_can_review(user_id, toilet_name):
    """【防洗評論】檢查該使用者是否已經評價過這間廁所"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        # 去資料庫找找看，這個 user_id 有沒有在同一間廁所留過言
        cursor.execute('SELECT id FROM reviews WHERE user_id = ? AND toilet_name = ?', (user_id, toilet_name))
        result = cursor.fetchone()
        
        # 如果 result 有東西，代表留過言了，回傳 False (不能再評價)
        return False if result else True
    except Exception as e:
        print(f"檢查評價紀錄失敗: {e}")
        return False
    finally:
        conn.close()

# --- 管理者後台專用功能 ---

def get_all_reviews_for_admin():
    """撈出系統內所有的評價，供後台列表顯示"""
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 關鍵修改：後台也一併轉換為台灣時間
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

# ----------------- 折價券與抽獎邏輯 -----------------

def setup_coupons_table():
    """確保 coupons 表格有數量欄位與發布帳號欄位 (如果沒有會自動建立)"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                coupon_text TEXT NOT NULL,
                target_keyword TEXT NOT NULL,
                total_quantity INTEGER DEFAULT 0,
                remaining_quantity INTEGER DEFAULT 0,
                admin_id INTEGER
            )
        ''')

        # 舊版 coupons 表格沒有 admin_id 欄位，就自動補上 (記錄是哪個廠商帳號發布的)
        cursor.execute('PRAGMA table_info(coupons)')
        columns = [row[1] for row in cursor.fetchall()]
        if 'admin_id' not in columns:
            cursor.execute('ALTER TABLE coupons ADD COLUMN admin_id INTEGER')

        conn.commit()
    except Exception as e:
        print(f"建立 coupons 表格失敗: {e}")
    finally:
        conn.close()
        
def add_coupon(vendor_name, coupon_text, target_keyword, quantity, admin_id):
    """新增一張折價券到資料庫，設定發行數量，並記錄發布的廠商帳號"""
    setup_coupons_table()
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        # 修正：將 quantity 同時存入總數量與剩餘數量
        cursor.execute('''
            INSERT INTO coupons (vendor_name, coupon_text, target_keyword, total_quantity, remaining_quantity, admin_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (vendor_name, coupon_text, target_keyword, quantity, quantity, admin_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"新增折價券失敗: {e}")
        return False
    finally:
        conn.close()

def get_all_coupons(admin_id=None):
    """撈出已發布的折價券 (有傳 admin_id 就只撈該廠商帳號發布的)"""
    setup_coupons_table()
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 使用 LEFT JOIN 關聯 admins 表，一併帶出發布帳號名稱
        if admin_id is None:
            cursor.execute('''
                SELECT c.*, a.username AS admin_username
                FROM coupons c
                LEFT JOIN admins a ON c.admin_id = a.id
                ORDER BY c.id DESC
            ''')
        else:
            cursor.execute('''
                SELECT c.*, a.username AS admin_username
                FROM coupons c
                LEFT JOIN admins a ON c.admin_id = a.id
                WHERE c.admin_id = ?
                ORDER BY c.id DESC
            ''', (admin_id,))
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

def setup_user_coupons_table():
    """建立使用者錢包資料表"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                coupon_id INTEGER NOT NULL,
                serial_code TEXT UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"建立 user_coupons 表格失敗: {e}")
    finally:
        conn.close()

def assign_coupon_to_user(user_id):
    """【必中機制與錢包紀錄】發放折價券並綁定使用者序號"""
    setup_user_coupons_table()
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 撈出還有庫存的折價券
        cursor.execute('SELECT * FROM coupons WHERE remaining_quantity > 0 ORDER BY RANDOM() LIMIT 1')
        coupon = cursor.fetchone()
        
        if coupon:
            # 2. 產生 8 碼不重複的大寫英數序號 (格式: XXXX-XXXX)
            code_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            serial_code = f"{code_str[:4]}-{code_str[4:]}"
            
            # 3. 扣除庫存
            cursor.execute('UPDATE coupons SET remaining_quantity = remaining_quantity - 1 WHERE id = ?', (coupon['id'],))
            
            # 4. 寫入該使用者的個人錢包
            cursor.execute('''
                INSERT INTO user_coupons (user_id, coupon_id, serial_code) 
                VALUES (?, ?, ?)
            ''', (user_id, coupon['id'], serial_code))
            
            conn.commit()
            
            # 將序號打包進去回傳給前端
            result = dict(coupon)
            result['serial_code'] = serial_code
            return result
            
        return None
    except Exception as e:
        print(f"分發折價券失敗: {e}")
        return None
    finally:
        conn.close()

def get_user_wallet(user_id):
    """撈取特定使用者的所有折價券清單"""
    setup_user_coupons_table()
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 使用 JOIN 關聯查詢，把 user_coupons 和 coupons 兩張表的資料拼起來
        cursor.execute('''
            SELECT uc.serial_code, uc.is_used, DATETIME(uc.created_at, '+8 hours') AS get_time,
                   c.vendor_name, c.coupon_text, c.target_keyword
            FROM user_coupons uc
            JOIN coupons c ON uc.coupon_id = c.id
            WHERE uc.user_id = ?
            ORDER BY uc.created_at DESC
        ''', (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"撈取錢包失敗: {e}")
        return []
    finally:
        conn.close()