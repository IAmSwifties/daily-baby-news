import os
import requests
import google.generativeai as genai
from datetime import datetime

# 從 GitHub Secrets 讀取設定
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_news_content():
    """
    這部分之後可以串接搜尋 API。
    目前我們先給 AI 一些關鍵字，讓它去生成（或是簡單抓取 Google News RSS）
    """
    # 這裡我們模擬抓到的育兒關鍵字
    return "腸病毒疫苗補助、兒童肥胖率調查、幼兒營養迷思、北市彈性育兒工時"

def generate_social_post(news):
    # 設定 Gemini
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    今天是 {datetime.now().strftime('%Y-%m-%d')}。
    你是專業的育兒社群小編，請針對以下主題撰寫一篇吸引人的社群文章：
    主題：{news}
    要求：
    1. 使用繁體中文，語氣親切有共鳴。
    2. 包含重點整理、爸媽小叮嚀。
    3. 加上豐富的 Emoji 並標註熱門標籤。
    4. 字數約 300-500 字。
    """
    response = model.generate_content(prompt)
    return response.text

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown" # 讓文字支援粗體等格式
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("正在處理今日新聞...")
    news_data = get_news_content()
    article = generate_social_post(news_data)
    send_to_telegram(article)
    print("訊息已成功傳送至 Telegram！")
