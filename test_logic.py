import os
import csv
import sqlite3  # 新增：之後用來連線操作資料庫
from urllib.parse import parse_qsl  # 新增：用來解析 Postback 按鈕藏的隱藏資料

from flask import Flask, request, abort
from geopy.distance import great_circle

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
# 下方 linebot.models 新增了 TemplateSendMessage, CarouselTemplate, CarouselColumn, PostbackAction, PostbackEvent
from linebot.models import (
    MessageEvent, LocationMessage, TextSendMessage, TextMessage, 
    QuickReply, QuickReplyButton, LocationAction,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, 
    PostbackAction, PostbackEvent
)
# 請確保 favorite_logic.py 跟 test_logic.py 放在同一個資料夾
from favorite_logic import add_favorite, get_my_favorites

app = Flask(__name__)

# ================= 1. 金鑰密鑰設定 (讀取雲端環境變數) =================
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ================= 2. 核心大腦 =================
# 伺服器開機時，先預載雙北廁所資料到大腦（只做一次）
toilets_data = []
try:
    with open('toilets.csv', mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = row['address']
            
            # 嚴格過濾雙北：確保地址的「最前面」是台北市或新北市
            if address.startswith('台北市') or address.startswith('臺北市') or address.startswith('新北市'):
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
            dist = great_circle((user_lat, user_lon), (t['lat'], t['lon'])).kilometers
            results.append({
                'name': t['name'],
                'address': t['address'],
                'distance': int(dist * 1000) # 轉成公尺，用 int() 去掉小數點
            })
        except Exception:
            continue

    results.sort(key=lambda x: x['distance'])
    return results[:5] 

# ================= 3. LINE 伺服器通訊接口 (Webhook) =================

@app.route("/")  # 新增：專門給UptimeRobot敲門用的
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
    # 步驟 A：抓取使用者的 ID
    user_id = event.source.user_id
    
    # 步驟 C：開始計算
    user_lat = event.message.latitude
    user_lon = event.message.longitude
    
    results = find_nearest_toilets_shuangbei(user_lat, user_lon)
    
    if not results:
        reply_msg = TextSendMessage(text="抱歉，目前在您的附近找不到公共廁所資訊")
        line_bot_api.reply_message(event.reply_token, reply_msg)
    else:
        # 準備建立「旋轉木馬模板」的卡片列表
        carousel_columns = []
        
        for t in results:
            # 防呆：確保文字沒有超過 LINE 的字數限制 (標題限制 40 字，內文限制 60 字)
            title_text = t['name'][:40]
            body_text = f"📍距離：約 {t['distance']} 公尺\n🚽地址：{t['address']}"[:60]
            
            # 取得廁所的ID (這裡假設妳的字典中有 'id' 這個鍵，如果沒有，請換成對應的變數)
            # 如果目前沒有 id，我們暫時先拿 t['name'] 當作資料庫紀錄用的ID 也可以
            toilet_id = t.get('id', t['name']) 
            
            # 製作單一張廁所卡片
            column = CarouselColumn(
                title=title_text,
                text=body_text,
                actions=[
                    # 這一顆就是專屬的Postback按鈕
                    PostbackAction(
                        label='加入收藏',
                        display_text=f'我想要收藏 {title_text}',
                        data=f'action=favorite&toilet_id={toilet_id}' # 把動作跟廁所ID偷藏進去
                    )
                ]
            )
            carousel_columns.append(column)
            
        # 把所有卡片組裝成一個完整的旋轉木馬訊息
        carousel_template_message = TemplateSendMessage(
            alt_text='為您找到附近的公廁資訊 (請在手機上查看)',
            template=CarouselTemplate(columns=carousel_columns)
        )
            
        # 步驟 D：把帶有按鈕的旋轉木馬卡片傳出去
        line_bot_api.reply_message(
            event.reply_token,
            carousel_template_message
        )

# ================= (新增) 處理 Postback 按鈕被點擊的事件 =================
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    
    # 解析按鈕裡面偷塞的隱藏資料 
    postback_data = dict(parse_qsl(event.postback.data))
    
    # 判斷這個按鈕是不是「收藏」動作
    if postback_data.get('action') == 'favorite':
        toilet_id = postback_data.get('toilet_id')
        
        # 關鍵整合：把抓到的 user_id 和 toilet_id，丟進妳寫好的資料庫函數裡！
        # 這裡的 result_msg 會收到 "已成功加入收藏！" 或 "已經在收藏名單"
        result_msg = add_favorite(user_id, toilet_id)
        
        # 把資料庫處理完的結果回覆給使用者
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result_msg)
        )

# ================= 5. 當手機傳送「文字」進來時 =================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text
    user_id = event.source.user_id  # 記得抓取使用者的ID
    
    # 處理找廁所的功能
    if user_text == '找廁所':
        reply_msg = TextSendMessage(
            text="請點擊下方按鈕，分享您的位置給我",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(
                        action=LocationAction(label="傳送我的位置")
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_msg)
   # 新增這一段：當使用者輸入「查看收藏」時
    elif user_text == '查看收藏':
        # 呼叫資料庫工具箱，去查這個 user_id 收藏了什麼
        result_msg = get_my_favorites(user_id)
        
        # 把查到的名單回傳給使用者
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result_msg)
        ) 

if __name__ == "__main__":
    app.run(port=5000)