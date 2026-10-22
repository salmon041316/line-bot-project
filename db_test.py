import sqlite3

# 連接到剛剛建立的資料庫檔案 (請確保這支程式跟 bot_data.db 在同一個資料夾)
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# 執行 SQL 語法：從 toilets 資料表中撈出前 3 筆資料
cursor.execute("SELECT * FROM toilets LIMIT 3")
results = cursor.fetchall()

# 印出結果
for row in results:
    print(row)

# 關閉連線
conn.close()