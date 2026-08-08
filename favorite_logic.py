# 第一步：讓Python自動建立「收藏」資料表
import sqlite3

def init_db():
    # 1. 連線到資料庫
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # 2. 建立favorites 收藏表
    # 欄位：id (流水號), user_id (使用者LINE ID), toilet_id (廁所編號)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            toilet_id INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("資料庫初始化完成，收藏表已就緒")
# 執行這段函數來建表
init_db()

# 第二步：撰寫「加入收藏」的邏輯
def add_favorite(user_id, toilet_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # 先檢查：這個user_id 是不是已經收藏過這個toilet_id 了？
    cursor.execute('''
        SELECT * FROM favorites 
        WHERE user_id = ? AND toilet_id = ?
    ''', (user_id, toilet_id))
    
    # 如果抓到資料，代表已經收藏過
    if cursor.fetchone():
        conn.close()
        return "已經在你的收藏名單囉！"
    
    # 如果沒收藏過，就新增一筆資料進去 (INSERT)
    cursor.execute('''
        INSERT INTO favorites (user_id, toilet_id) 
        VALUES (?, ?)
    ''', (user_id, toilet_id))
    
    conn.commit()
    conn.close()
    return "已成功加入收藏！"

# 第三步：撰寫「查看我的收藏」邏輯
def get_my_favorites(user_id):
    import sqlite3 
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT toilet_id 
        FROM favorites 
        WHERE user_id = ?
    ''', (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    # 準備一個空清單
    favorites_list = []
    
    # 把找到的名字一個個放進清單裡
    for row in results:
        favorites_list.append(row[0])
        
    # 直接回傳這個清單給主程式
    return favorites_list

def remove_favorite(user_id, toilet_id):
    import sqlite3 
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # 步驟 1：先檢查這間廁所是不是真的有在收藏名單裡？
    cursor.execute('''
        SELECT * FROM favorites 
        WHERE user_id = ? AND toilet_id = ?
    ''', (user_id, toilet_id))
    
    if not cursor.fetchone():
        conn.close()
        return "這間廁所不在收藏名單內"
    
    # 步驟 2：如果有在名單裡，就執行 DELETE 把它刪掉
    cursor.execute('''
        DELETE FROM favorites 
        WHERE user_id = ? AND toilet_id = ?
    ''', (user_id, toilet_id))
    
    conn.commit()
    conn.close()
    return "💔已取消收藏"