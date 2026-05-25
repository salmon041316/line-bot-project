import os
import csv
from flask import Flask, request, abort
from geopy.distance import geodesic

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, LocationMessage, TextSendMessage, TextMessage, QuickReply, QuickReplyButton, LocationAction

app = Flask(__name__)

# ================= 1. 金鑰密鑰設定 (讀取雲端環境變數) =================
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ================= 2. 核心大腦（記憶體極速優化版） =================
# 伺服器開機時，先預載雙北廁所資料到大腦（只做一次）
toilets_data = []
try:
    with open('toilets.csv', mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = row['address']
            # 過濾雙北
            if '台北' in address or '臺北' in address or '新北' in address:
                toilets_data.append({
                    'name': row['name'],
                    'address': address,
                    'lat': float(row['latitude']),
                    'lon': float(row['longitude'])
                })
except Exception as e:
    print(f"讀取 CSV 發生錯誤: {e}")

# 當使用者傳定位時，直接從大腦算距離
def find_nearest_toilets_shuangbei(user_lat, user_lon):
    results = []
    for t in toilets_data:
        try:
            dist = geodesic((user_lat, user_lon), (t['lat'], t['lon'])).kilometers
            results.append({
                'name': t['name'],
                'address': t['address'],
                'distance': int(dist * 1000) # 乘以 1000 轉成公尺，用 int() 去掉小數點
            })
        except Exception:
            continue

    results.sort(key=lambda x: x['distance'])
    return results[:5] 

# ================= 3. LINE 伺服器通訊接口 (Webhook) =================

@app.route("/")  # 新增：專門給網路鬧鐘敲門用的首頁
def home():
    return "Hello! LINE Bot is alive!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ================= 4. 當手機傳送「位置資訊」進來時 =================
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    # 步驟 A：偷偷抓取使用者的專屬 ID (做資料庫「收藏」功能的重要關鍵！)
    user_id = event.source.user_id
    
    # 步驟 B：大腦開始運算前，先用 Push Message 推播「請稍等」的提示
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text="抓取定位資料及廁所資料中...\n請稍等")
    )

    # 步驟 C：開始原本的辛苦計算
    user_lat = event.message.latitude
    user_lon = event.message.longitude
    
    results = find_nearest_toilets_shuangbei(user_lat, user_lon)
    
    if not results:
        reply_text = "抱歉，目前在您的附近找不到雙北地區的公共廁所資訊。"
    else:
        reply_text = "為您找到距離最近的 5 個雙北公廁：\n\n"
        for i, t in enumerate(results, 1):
            reply_text += f"{i}. 【{t['name']}】\n"
            reply_text += f"   地址：{t['address']}\n"
            reply_text += f"   距離：約 {t['distance']} 公尺\n"
            reply_text += "------------------------\n"
            
    # 步驟 D：算完之後，用 Reply Token 把結果傳出去
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text.strip())
    )

# ================= 5. 當手機傳送「文字」進來時 =================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text
    
    # 處理找廁所的功能
    if user_text == '找廁所':
        reply_msg = TextSendMessage(
            text="請點擊下方按鈕，分享您的位置給我！",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(
                        action=LocationAction(label="傳送我的位置")
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_msg)

if __name__ == "__main__":
    app.run(port=5000)