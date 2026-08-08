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
    PostbackAction, PostbackEvent, FlexSendMessage
)
# 請確保 favorite_logic.py 跟 test_logic.py 放在同一個資料夾
from favorite_logic import add_favorite, get_my_favorites, remove_favorite

app = Flask(__name__)

# ================= 1. 金鑰密鑰設定 (讀取雲端環境變數) =================
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ================= 2. 核心資料庫運算 =================
# 當使用者傳送定位時，直接從「資料庫」撈出所有廁所來計算距離
def find_nearest_toilets_shuangbei(user_lat, user_lon):
    import sqlite3
    from geopy.distance import great_circle

    # 1. 連線到資料庫
    conn = sqlite3.connect('bot_data.db')
    
    # 讓資料庫撈出來的資料變成「字典 (Dictionary)」的格式
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 2. 從資料庫把所有的廁所撈出來
    cursor.execute("SELECT * FROM toilets")
    all_toilets = cursor.fetchall()
    conn.close()
    
    results = []
    
    # 3. 迴圈計算每一間廁所的距離
    for t in all_toilets:
        try:
            # 如果資料庫裡的經緯度欄位是中文，請改成資料庫裡欄位名稱
            toilet_lat = float(t['latitude'])  
            toilet_lon = float(t['longitude'])
            
            # 計算距離 (公尺)
            dist = great_circle((user_lat, user_lon), (toilet_lat, toilet_lon)).meters
            
            # 把計算結果存進陣列裡
            # 這裡的 'address' 如果資料庫裡的欄位是中文，請改成資料庫裡欄位名稱
            results.append({
                'name': t['name'],
                'address': t['address'], 
                'distance': round(dist)
            })
        except Exception:
            # 萬一某筆廁所資料剛好沒有經緯度，就跳過它，避免程式崩潰
            continue
            
    # 4. 根據距離 (distance) 由小到大排序 (也就是由近到遠)
    results = sorted(results, key=lambda x: x['distance'])
    
    # 5. 回傳前 5 名
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
            # 沒有 id，我們暫時先拿 t['name'] 當作資料庫紀錄用的ID
            toilet_id = t.get('id', t['name']) 
            
            # 製作單一張廁所卡片
            column = CarouselColumn(
                title=title_text,
                text=body_text,
                actions=[
                    # 原本的加入收藏按鈕
                    PostbackAction(
                        label='加入收藏❤️',
                        display_text=f'收藏 {title_text}',
                        data=f'action=favorite&toilet_id={toilet_id}' 
                    ),
                    # 🌟 新增的取消收藏按鈕
                    PostbackAction(
                        label='取消收藏💔',
                        display_text=f'取消收藏 {title_text}',
                        data=f'action=unfavorite&toilet_id={toilet_id}' # 這裡的action 變成了unfavorite
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
    postback_data = dict(parse_qsl(event.postback.data))
    
    # 判斷是不是「加入收藏」
    if postback_data.get('action') == 'favorite':
        toilet_id = postback_data.get('toilet_id')
        result_msg = add_favorite(user_id, toilet_id)
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result_msg))
        
    # 新增：判斷是不是「取消收藏」
    elif postback_data.get('action') == 'unfavorite':
        toilet_id = postback_data.get('toilet_id')
        
        # 呼叫刪除函數
        result_msg = remove_favorite(user_id, toilet_id)
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result_msg))

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
        # 1. 先去資料庫拿名單 (現在會拿到一個 List)
        favorites_list = get_my_favorites(user_id)
        
        # 2. 判斷名單是不是空的
        if not favorites_list:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="你還沒有收藏任何廁所")
            )
        else:
            # 3. 如果有名單，就把名單丟進製造機，做成Flex Message
            flex_content = create_favorites_flex(favorites_list)
            
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="你的收藏名單", contents=flex_content)
            )
           
def create_favorites_flex(favorites_list):
    # 這是卡片最上方的標題區塊
    contents = [
        {"type": "text", "text": "❤️ 我的收藏名單", "weight": "bold", "size": "xl", "color": "#E55B5B"},
        {"type": "text", "text": "點選下方按鈕可進行管理或查看路線", "size": "xs", "color": "#999999", "margin": "sm"},
        {"type": "separator", "margin": "md"}
    ]
    
    # 透過迴圈，根據名單數量動態產生對應數量的項目與按鈕
    for i, name in enumerate(favorites_list, 1):
        # 加入廁所名稱
        contents.append({"type": "text", "text": f"{i}. {name}", "weight": "bold", "size": "sm", "margin": "md"})
        
        # 加入一排兩個按鈕 (水平排列)
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "color": "#E3E7E8",  # 淺灰色
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🗑️ 刪除",
                        "data": f"action=unfavorite&toilet_id={name}"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#769382",  # 莫蘭迪綠
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📍 查看資訊",
                        "data": f"action=view_info&toilet_id={name}" # 預留給未來的查看資訊功能
                    }
                }
            ]
        })
        
    # 最後把所有內容包裝成 Flex Message 規定的格式
    flex_dict = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": contents}
    }
    return flex_dict

if __name__ == "__main__":
    app.run(port=5000)