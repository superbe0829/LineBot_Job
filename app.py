# -*- coding: utf-8 -*-
import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from bs4 import BeautifulSoup

# 初始化 Flask 應用程式
app = Flask(__name__)

# Line Bot Token & Secret (從環境變數中提取)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 爬取最新徵才活動資料
def fetch_job_events():
    url = "https://ilabor.ntpc.gov.tw/cloud/GoodJob/activities"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        events = soup.find_all("div", class_="event-item")

        formatted_events = []
        for idx, event in enumerate(events[:10], start=1):
            name = event.find("div", class_="event-item-name").text.strip()
            link = event.find("a")["href"]
            formatted_events.append(f"{idx}. {name}\n詳細資訊：{link}")

        return formatted_events
    except Exception as e:
        print(f"Error fetching job events: {e}")
        return []

# 爬取服務據點清單
def fetch_service_locations():
    base_url = "https://ilabor.ntpc.gov.tw"
    url = f"{base_url}/browse/employment-service/employment-service-branch"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        location_elements = soup.find_all("a", class_="list-group-item")

        service_locations = []
        for element in location_elements:
            name_tag = element.find("p", class_="tit-h4-b")
            if name_tag and ("服務站" in name_tag.text or "服務台" in name_tag.text):
                name = name_tag.text.strip()
                relative_url = element["href"]
                full_url = f"{base_url}{relative_url}"
                service_locations.append(f"{name}，詳細資訊：{full_url}")

        return service_locations[:10]  # 返回前 10 筆
    except Exception as e:
        print(f"Error fetching service locations: {e}")
        return []

# Line Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理 Line 訊息
@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()

    if "@徵才活動" in user_message:
        events = fetch_job_events()
        if events:
            reply_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(events)
        else:
            reply_message = "抱歉，目前無法提供徵才活動資訊。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@服務據點" in user_message:
        locations = fetch_service_locations()
        if locations:
            reply_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations)
        else:
            reply_message = "目前無法取得服務據點資訊。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@人資宣導" in user_message:
        try:
            message = ImageSendMessage(
                original_content_url="https://example.com/image.jpg",
                preview_image_url="https://example.com/image.jpg"
            )
            line_bot_api.reply_message(event.reply_token, message)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"發生錯誤：{e}"))

    else:
        reply_message = "請點擊下方服務快捷鍵取得所需資訊！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

# Flask 入口點（符合 Vercel 要求）
@app.route("/")
def index():
    return "LINE Bot is running!"

# 確保應用在本地運行時啟動
if __name__ == "__main__":
    app.run(debug=True)
