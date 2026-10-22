import os
import csv
import sqlite3  # 新增：之後用來連線操作資料庫
import random
from urllib.parse import parse_qsl, quote  # 新增：用來解析 Postback 按鈕藏的隱藏資料

from flask import Flask, request, abort, render_template, jsonify
from review_logic import (
    save_review_to_db, get_reviews_by_toilet, get_latest_reviews, 
    search_toilets_from_master, check_user_can_review, get_all_reviews_for_admin, 
    delete_review_by_id, add_coupon, get_all_coupons, get_user_review_count, 
    get_available_coupon
)
from geopy.distance import great_circle

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
# 下方 linebot.models 新增了 TemplateSendMessage, CarouselTemplate, CarouselColumn, PostbackAction, PostbackEvent
from linebot.models import (
    MessageEvent, LocationMessage, TextSendMessage, TextMessage, 
    QuickReply, QuickReplyButton, LocationAction,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, 
    PostbackAction, PostbackEvent, FlexSendMessage, URIAction, 
    ButtonsTemplate, URITemplateAction, MessageTemplateAction
)
# 請確保 favorite_logic.py 跟 main.py 放在同一個資料夾
from favorite_logic import add_favorite, get_my_favorites, remove_favorite
from flex_templates import create_toilet_flex_message, create_favorites_flex

from flask import session
from werkzeug.security import generate_password_hash, check_password_hash

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

# ================= 3. 伺服器路由與 API 通道 (Routes & API Endpoints) =================

# ---------------------------------------------------------
# 【系統與 LINE 核心機制】
# ---------------------------------------------------------

@app.route("/")
def home():
    """提供給 UptimeRobot 監控伺服器存活狀態使用的根目錄"""
    return "Hello! LINE Bot is alive!"

@app.route("/callback", methods=['POST'])
def callback():
    """接收 LINE Server 傳來的 Webhook 訊息與事件"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# ---------------------------------------------------------
# 【前端網頁渲染 (HTML Pages)】
# ---------------------------------------------------------

@app.route('/review')
def render_review_page():
    """顯示「撰寫評價」網頁表單"""
    return render_template('review.html')

@app.route('/view_reviews')
def view_reviews_page():
    """顯示「查看廁所評價與雙軌搜尋」網頁"""
    return render_template('view_reviews.html')

# ---------------------------------------------------------
# 【評價與搜尋系統 API (給前端網頁呼叫用)】
# ---------------------------------------------------------

@app.route('/api/review', methods=['POST'])
def submit_review():
    data = request.json
    user_id = data.get('user_id')
    toilet_name = data.get('toilet_name')
    stars = data.get('stars')
    comment = data.get('comment')
    
    # 1. 防洗版檢查
    if not check_user_can_review(user_id, toilet_name):
        return jsonify({"status": "error", "message": "您已經評價過這間廁所囉！把機會留給其他間吧！"}), 400

    # 2. 儲存評價
    if save_review_to_db(user_id, toilet_name, stars, comment):
        # 3. 取得該使用者的總評價數
        review_count = get_user_review_count(user_id)
        
        # 4. 判斷是否達標 (5 的倍數)
        if review_count % 5 == 0:
            # 滿 5 次，發放折價券 (直接抓取庫存)
            coupon = get_available_coupon()
            if coupon:
                return jsonify({
                    "status": "success", 
                    "reward": True,
                    "review_count": review_count,
                    "coupon": coupon
                })
            else:
                return jsonify({
                    "status": "success", 
                    "reward": False,
                    "review_count": review_count,
                    "message": "感謝評價！您已滿 5 則評價，但目前折價券已被索取完畢，敬請期待下一波活動！"
                })
        else:
            # 未滿 5 次，一般累積中
            return jsonify({
                "status": "success",
                "reward": False,
                "review_count": review_count,
                "message": "評價送出成功！"
            })

    return jsonify({"status": "error", "message": "評價儲存失敗"}), 500

# ---------------------------------------------------------
# 【前端讀取與搜尋評價 API】
# ---------------------------------------------------------

@app.route('/api/reviews/latest', methods=['GET'])
def api_get_latest_reviews_only():
    """前端網頁用來抓取「最新評價」的專屬通道"""
    data = get_latest_reviews()
    return jsonify(data)

@app.route('/api/reviews/<keyword>', methods=['GET'])
def api_search_reviews_by_keyword(keyword):
    """前端網頁用來「搜尋特定廁所評價」的動態路徑通道 (解決 404 錯誤)"""
    # 專門接住前端把關鍵字直接放在網址後面的請求，例如 /api/reviews/西門
    data = get_reviews_by_toilet(keyword)
    return jsonify(data)

@app.route('/api/reviews', methods=['GET'])
def api_get_reviews():
    """前端網頁用來「搜尋特定廁所評價」的查詢參數通道 (預防前端使用 ?keyword= 格式)"""
    keyword = request.args.get('keyword', '').strip()
    
    if keyword:
        # 有輸入關鍵字：搜尋特定廁所的評價
        data = get_reviews_by_toilet(keyword)
    else:
        # 沒輸入關鍵字：預設顯示最新評價
        data = get_latest_reviews()
        
    return jsonify(data)

@app.route('/api/search_toilets/<keyword>', methods=['GET'])
def api_search_toilets_by_keyword(keyword):
    """前端網頁用來「搜尋廁所基本資料」的動態路徑通道 (解決 404 錯誤)"""
    # 專門接住 /api/search_toilets/西門 這種請求
    data = search_toilets_from_master(keyword)
    return jsonify(data)

@app.route('/api/search_toilets', methods=['GET'])
def api_search_toilets():
    """雙軌搜尋功能：只用關鍵字找廁所基本資料 (保留給預防萬一的查詢參數格式)"""
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify([])
    
    data = search_toilets_from_master(keyword)
    return jsonify(data)

# ==========================================
# 🛡️ 營運後台專區 (Session 憑證與密碼加密)
# ==========================================

# 🌟 設定 Session 必備的加密鑰匙 (絕對不能外流)
app.secret_key = 'your_graduation_project_secret_key'

def init_admin_account():
    """【系統啟動時自動執行】建立管理員資料表與預設帳號"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        # 1. 建立 admins 資料表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        # 2. 檢查是否已經有 admin 這個帳號
        cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
        if not cursor.fetchone():
            # 3. 如果沒有，就建立預設帳號 (帳號: admin, 密碼: !QAZ2wsxadmin)
            # 🌟 注意：存進資料庫的是 generate_password_hash 產生的一長串亂碼，不是明碼！
            hashed_pwd = generate_password_hash('!QAZ2wsxadmin')
            cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ('admin', hashed_pwd))
            conn.commit()
    except Exception as e:
        print(f"建立管理員帳號失敗: {e}")
    finally:
        conn.close()

# 在啟動伺服器前，先呼叫函數把帳號建好
init_admin_account()


@app.route('/admin')
def admin_page():
    """回傳管理員後台網頁"""
    return render_template('admin.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """負責核對帳號密碼，並核發 Session 通行證"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    try:
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        admin = cursor.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()

    # 🌟 驗證密碼：使用 check_password_hash 比對前端傳來的密碼與資料庫裡的亂碼
    if admin and check_password_hash(admin['password_hash'], password):
        # 密碼正確，發放通行證 (存在伺服器記憶體中)
        session['admin_logged_in'] = True
        return jsonify({"status": "success", "message": "登入成功"})
    else:
        return jsonify({"status": "error", "message": "帳號或密碼錯誤"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """登出：銷毀 Session 通行證"""
    session.clear()
    return jsonify({"status": "success"})

# ---新增帳號密碼---

@app.route('/api/admin/accounts', methods=['POST'])
def api_create_admin_account():
    """讓已登入的管理員，能在後台建立新的廠商帳號"""
    # 1. 檢查是否已經登入 (防護機制)
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "無權限存取，請先登入"}), 401
        
    data = request.json
    new_username = data.get('username')
    new_password = data.get('password')
    
    if not new_username or not new_password:
        return jsonify({"status": "error", "message": "帳號與密碼不能為空！"}), 400
        
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # 2. 檢查帳號是否已經被別人註冊走了
        cursor.execute("SELECT id FROM admins WHERE username = ?", (new_username,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "此帳號已經存在，請換一個名稱！"}), 400
            
        # 3. 密碼加密並寫入資料庫
        hashed_pwd = generate_password_hash(new_password)
        cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", (new_username, hashed_pwd))
        conn.commit()
        
        return jsonify({"status": "success", "message": f"成功建立新廠商帳號：{new_username}"})
    except Exception as e:
        print(f"建立帳號失敗: {e}")
        return jsonify({"status": "error", "message": "伺服器發生錯誤"}), 500
    finally:
        conn.close()

# ---------------- 以下是需要「憑證」才能存取的 API ----------------

@app.route('/api/admin/reviews', methods=['GET'])
def api_admin_get_reviews():
    """讀取所有評價 (檢查 Session)"""
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "無權限存取，請先登入"}), 401
    reviews = get_all_reviews_for_admin()
    return jsonify(reviews)

@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
def api_admin_delete_review(review_id):
    """刪除特定評價 (檢查 Session)"""
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "無權限存取，請先登入"}), 401
    if delete_review_by_id(review_id):
        return jsonify({"status": "success", "message": "刪除成功"})
    return jsonify({"status": "error", "message": "刪除失敗"}), 500

@app.route('/api/admin/coupons', methods=['GET'])
def api_admin_get_coupons():
    """讀取折價券清單 (檢查 Session)"""
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "無權限存取，請先登入"}), 401
    coupons = get_all_coupons()
    return jsonify(coupons)

@app.route('/api/admin/coupons', methods=['POST'])
def api_add_coupon():
    """發布新折價券 (檢查 Session)"""
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "無權限存取，請先登入"}), 401
        
    data = request.json
    vendor_name = data.get('vendor_name')
    coupon_text = data.get('coupon_text')
    target_keyword = data.get('target_keyword')
    quantity = data.get('quantity')
    
    if not quantity or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"status": "error", "message": "發布失敗：請設定正確的發放數量！"}), 400

    if add_coupon(vendor_name, coupon_text, target_keyword, quantity):
        return jsonify({"status": "success", "message": "折價券發布成功"})
    return jsonify({"status": "error", "message": "發布失敗，請稍後再試"}), 500

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
        # 準備建立「Flex Message」的美編卡片列表
        flex_bubbles = []

        for i, t in enumerate(results, start=1):
            toilet_name = t['name']
            distance = t['distance']
            address = t['address']

            # 處理網址編碼 (供地圖和 LIFF 使用)
            encoded_name = quote(toilet_name)

            # 這裡直接呼叫剛剛搬到 flex_templates.py 的函數！
            bubble = create_toilet_flex_message(i, toilet_name, distance, address, encoded_name)

            # 把設定好的卡片加進列表中
            flex_bubbles.append(bubble)
            
        # 將裝滿美編卡片的 flex_bubbles 包裝成輪播 (carousel) 格式發送
        flex_message = FlexSendMessage(
            alt_text="為您找到附近的廁所囉！",
            contents={
                "type": "carousel",
                "contents": flex_bubbles
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

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
    # 新增這一段：處理評價選單
    elif user_text == '寫評價、查看評價':
        buttons_template = TemplateSendMessage(
            alt_text='評價功能選單',
            template=ButtonsTemplate(
                title='廁所評價系統',
                text='請選擇您想要使用的功能：',
                actions=[
                    # 第一顆按鈕：開啟查看評價網頁
                    URITemplateAction(
                        label='🔍 查看評價',
                        uri='https://line-bot-project-fn7r.onrender.com/view_reviews'
                    ),
                    # 第二顆按鈕：點擊後機器人會自動回覆教學文字
                    MessageTemplateAction(
                        label='✏️ 怎麼寫評價？',
                        text='【如何寫評價？】\n請先點選下方選單的「地址」搜尋，找到目標廁所後，直接點擊卡片下方的「⭐ 留下評價」按鈕，就可以開始評分囉！'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

if __name__ == "__main__":
    app.run(port=5000)