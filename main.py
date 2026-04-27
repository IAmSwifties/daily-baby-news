import os
import requests
from google import genai # 改用新版套件
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_news_content():
    return "腸病毒疫苗補助、兒童肥胖率調查、幼兒營養迷思、北市彈性育兒工時"

def generate_social_post(news):
    # 新版的設定與呼叫方式
    client = genai.Client(api_key=GEMINI_KEY)
    
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
    
    # 使用新版指令產生內容
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt
    )
    return response.text

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("正在處理今日新聞...")
    news_data = get_news_content()
    article = generate_social_post(news_data)
    send_to_telegram(article)
    print("訊息已成功傳送至 Telegram！")
