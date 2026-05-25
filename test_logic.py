import os
import csv
from flask import Flask, request, abort
from geopy.distance import geodesic

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, LocationMessage, TextSendMessage

app = Flask(__name__)

# ================= 1. 金鑰密鑰設定（等組員貼給你） =================
LINE_CHANNEL_SECRET = '76cca12c423b8d34432f38c3a07f490b'
LINE_CHANNEL_ACCESS_TOKEN = 'kHK6WHMfFUXM82vP29eoczpIB8QNKuZ2pbgYHcu19Oqfsd6CvLTRlRUXMZGxFtISzzwkwyOVE8uy0XcA79pyK+YzS1BbHhHKl4JBq7hhgTtYXpE2J8FNwSDSJY+JuWQde20HfZTiHU8yc6OZvxZ7UAdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ================= 2. 核心大腦（公廁距離演算法） =================
def find_nearest_toilets_shuangbei(user_lat, user_lon, csv_file='toilets.csv'):
    toilets = []
    with open(csv_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                address = row['address']
                # 自動篩選雙北
                if '台北' in address or '臺北' in address or '新切' in address or '新北' in address:
                    t_lat = float(row['latitude'])
                    t_lon = float(row['longitude'])
                    t_name = row['name']
                    
                    dist = geodesic((user_lat, user_lon), (t_lat, t_lon)).kilometers
                    toilets.append({
                        'name': t_name,
                        'address': address,
                        'distance': round(dist, 2)
                    })
            except Exception as e:
                continue

    toilets.sort(key=lambda x: x['distance'])
    return toilets[:5] # 取最近的 5 間，手機畫面比較好閱讀

# ================= 3. LINE 伺服器通訊接口 (Webhook) =================
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ================= 4. 核心：當手機傳送「位置資訊」進來時 =================
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    #核心 A：自動抓取使用者手機傳來的精準經緯度
    user_lat = event.message.latitude
    user_lon = event.message.longitude
    
    #核心 B：丟進大腦計算最近的 5 個雙北公廁
    results = find_nearest_toilets_shuangbei(user_lat, user_lon)
    
    #核心 C：把結果包裝成文字，準備回傳給使用者的 LINE
    if not results:
        reply_text = "抱歉，目前在您的附近找不到雙北地區的公共廁所資訊。"
    else:
        reply_text = "為您找到距離最近的 5 個雙北公廁：\n\n"
        for i, t in enumerate(results, 1):
            reply_text += f"{i}. 【{t['name']}】\n"
            reply_text += f"   地址：{t['address']}\n"
            reply_text += f"   距離：約 {t['distance']} 公里\n"
            reply_text += "------------------------\n"
            
    #核心 D：將訊息發送回手機端
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text.strip())
    )

if __name__ == "__main__":
    app.run(port=5000)