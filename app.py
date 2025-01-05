# -*- coding: utf-8 -*-
print()
print("=========================")
print("Program：FamDataRead")
print("Author： Chang Pi-Tsao")
print("Created on Jan. 5  2025")
print("=========================")
print()

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup
import os

# 初始化 Flask 應用程式
app = Flask(__name__)

# Line Bot Token & Secret (從 Line Developers Console 取得)
# LINE_CHANNEL_ACCESS_TOKEN = '你的Channel Access Token'
# LINE_CHANNEL_SECRET = '你的Channel Secret'
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 爬取最新徵才活動資料
def fetch_job_events():
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.implicitly_wait(10)
    url = "https://ilabor.ntpc.gov.tw/cloud/GoodJob/activities"
    driver.get(url)
    events = driver.find_elements(By.CLASS_NAME, "event-item")
    
    formatted_events = []
    for idx, event in enumerate(events, start=1):
        date = event.get_attribute("data-date")
        name = event.find_element(By.CLASS_NAME, "event-item-name").text.strip()
        link = event.get_attribute("href")
        # formatted_events.append(f"{idx}. {date}：{name}\n詳細資訊：{link}")
        formatted_events.append(f"{idx}. {name}\n，詳細資訊：{link}")
    
    driver.quit()
    return formatted_events

# # 爬取服務據點清單（使用Selenium語法）
# def fetch_service_locations():
#     driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
#     driver.implicitly_wait(10)
#     url = "https://ilabor.ntpc.gov.tw/browse/employment-service/employment-service-branch"
#     driver.get(url)
#     # 抓取 <p class="tit-h4-b"> 的文字內容
#     locations = driver.find_elements(By.CLASS_NAME, "tit-h4-b")
#     service_locations = [
#         location.text.strip()
#         for location in locations
#         if location.text.strip() and ("服務站" in location.text or "服務台" in location.text)
#     ]
#     driver.quit()
#     return service_locations

# 爬取服務據點清單（使用Request）
# def fetch_service_locations():
#     # global service_locations
#     url = "https://ilabor.ntpc.gov.tw/browse/employment-service/employment-service-branch"
    
#     try:
#         # 發送 GET 請求取得網頁內容
#         response = requests.get(url)
#         response.raise_for_status()  # 檢查 HTTP 狀態碼
#         html_content = response.text

#         # 使用 BeautifulSoup 解析 HTML
#         soup = BeautifulSoup(html_content, "html.parser")
        
#         # 抓取所有 <p class="tit-h4-b"> 的內容
#         location_elements = soup.find_all("p", class_="tit-h4-b")
        
#         service_locations = [
#             element.text.strip()
#             for element in location_elements
#             if "服務站" in element.text or "服務台" in element.text
#         ]

#         # 去重處理
#         unique_locations = list(dict.fromkeys(service_locations))
        
#         # 加上序號
#         numbered_locations = [
#            f"{idx + 1}. {location}" for idx, location in enumerate(unique_locations)
#            ]
        
#         # return unique_locations
#         return numbered_locations
        
#     except Exception as e:
#         print(f"發生錯誤：{e}")
#         return []

# 爬取服務據點清單（使用Request）
def fetch_service_locations():
    base_url = "https://ilabor.ntpc.gov.tw"
    url = f"{base_url}/browse/employment-service/employment-service-branch"
    
    try:
        # 發送 GET 請求取得網頁內容
        response = requests.get(url)
        response.raise_for_status()  # 檢查 HTTP 狀態碼
        html_content = response.text

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 抓取所有 <a> 標籤
        location_elements = soup.find_all("a", class_="list-group-item")
        service_locations = []

        for element in location_elements:
            # 提取名稱
            name_tag = element.find("p", class_="tit-h4-b")
            if name_tag and ("服務站" in name_tag.text or "服務台" in name_tag.text):
                name = name_tag.text.strip()
                # 提取相對 URL 並組合完整 URL
                relative_url = element["href"]
                full_url = f"{base_url}{relative_url}"
                # 添加名稱與連結
                service_locations.append((name, full_url))
        
        # 去重處理
        unique_locations = list(dict.fromkeys(service_locations))

        # 加上序號與連結
        numbered_locations = [
            f"{idx + 1}. {name}，詳細資訊：{link}" 
            for idx, (name, link) in enumerate(unique_locations)
        ]

        return numbered_locations

    except Exception as e:
        print(f"發生錯誤：{e}")
        return []


# Line Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理 Line 訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # user_message = event.message.text.strip().lower()
    user_message = event.message.text
    
    if "@徵才活動" in user_message:
        try:
            events = fetch_job_events()
            # reply_message = "\n\n".join(events[:5])  # 回覆前 5 筆資料
            # reply_message = "\n\n".join(events)
            reply_message = "\n\n".join(events[:10])
            reply_message = "以下是近期10場最新徵才活動：\n" + reply_message
        except Exception as e:
            reply_message = f"抱歉，目前無法提供資訊。\n錯誤：{e}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
    
    # elif mtext == '@傳送圖片':
    elif "@人資宣導" in user_message:
        try:
            message = ImageSendMessage(
                original_content_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
                preview_image_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
            )
            line_bot_api.reply_message(event.reply_token, message)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'發生錯誤：{e}'))
    
    elif "@服務據點" in user_message:
        try:
            locations = fetch_service_locations()
            # locations, s_locations = fetch_service_locations()
            # print(s_locations)
            if locations:
                reply_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations)
            else:
                reply_message = "目前無法取得服務據點資訊。"
        except Exception as e:
            reply_message = f"抱歉，無法提供服務據點資訊。\n錯誤：{e}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
    
    else:
        reply_message = "請點擊下方服務快捷鍵取得所需資訊！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

# print(service_locations)

# 啟動伺服器
if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=5000)
    app.run()
