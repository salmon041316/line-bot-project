import sqlite3

# 1. 連線到妳現有的資料庫
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# 2. 建立 reviews (評價) 資料表
# 使用 IF NOT EXISTS 確保如果已經建過，就不會重複建立或報錯
cursor.execute('''
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,          -- 留言者的 LINE ID
    toilet_name TEXT NOT NULL,      -- 被評價的廁所名稱
    stars INTEGER NOT NULL,         -- 星星數 (1~5)
    comment TEXT,                   -- 文字留言 (可以不填，所以不加 NOT NULL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 系統自動記錄留言時間
)
''')

# 3. 儲存變更並關閉連線
conn.commit()
conn.close()

print("reviews 評價資料表建立成功！")