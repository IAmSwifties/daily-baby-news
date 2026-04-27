import os
import time
import requests
from google import genai
from datetime import datetime
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_news_content():
    print("開始搜尋 Google 新聞並抓取內文...")
    keywords = "育兒"
    query = urllib.parse.quote(f"{keywords} when:1d")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

    keywords = '育兒 (營養 OR 補助 OR 疾病 OR 安全)'
    query = urllib.parse.quote(f"{keywords} when:1d")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        news_data_list = []
        # 加入 headers 偽裝成瀏覽器，降低被擋機率
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            
            print(f"正在讀取: {title[:20]}...")
            
            try:
                # 點進新聞連結抓內文
                article_req = requests.get(link, headers=headers, timeout=10)
                soup = BeautifulSoup(article_req.content, 'html.parser')
                
                # 找尋網頁中的段落標籤 <p>
                paragraphs = soup.find_all('p')
                
                # 把所有段落都抓下來，但限制總字數避免某些極端長文讓程式卡住
                content_list = [p.text.strip() for p in paragraphs if p.text.strip()]
                full_content = " ".join(content_list)
                # 限制每篇文章最多給 AI 讀 1500 字，這對台灣新聞來說已經非常夠了
                content = full_content[:1500]
                
                if content:
                    news_data_list.append(f"【標題】：{title}\n【內容摘要】：{content}\n【連結】：{link}\n")
            except Exception as e:
                print(f"這篇無法讀取內文跳過：{e}")
                pass
            
            # 限制只抓前 3 篇，避免資料量太大讓 AI 處理過久或出錯
            if len(news_data_list) >= 5:
                break
                
        if news_data_list:
            final_news = "\n".join(news_data_list)
            print("新聞內文抓取完成！")
            return final_news
        else:
            print("今天沒有抓到相關新聞內文喔！")
            return "今天沒有特別重大的育兒新聞。"
            
    except Exception as e:
        print(f"抓新聞時發生錯誤: {e}")
        return "無法取得今日新聞，請稍後再試。"

def generate_social_post(news):
    client = genai.Client(api_key=GEMINI_KEY)
    
    prompt = f"""
    今天是 {datetime.now().strftime('%Y-%m-%d')}。
    你是專業的育兒社群小編，請針對以下主題撰寫一篇吸引人的社群文章：
    
    新聞素材：
    {news}
    
    要求：
    1. 使用繁體中文，語氣親切有共鳴。
    2. 包含重點整理、爸媽小叮嚀。
    3. 加上豐富的 Emoji 並標註熱門標籤。
    4. 字數小於500 字。
    5. 絕對不要使用 Markdown 語法 (例如 ** 或 * 或 #)，純文字呈現即可。
    6. 文章最後必須附上新聞素材中提供的【連結】作為參考資料。
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3-flash-preview', 
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"第 {attempt + 1} 次嘗試失敗，錯誤訊息：{e}")
            if attempt < max_retries - 1:
                print("等待 10 秒後重試...")
                time.sleep(10)
            else:
                return "今天 AI 罷工了，請稍後再試！😭"

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        # 維持註解狀態，確保不會因為奇怪的符號導致 Telegram 報錯
        # "parse_mode": "Markdown" 
    }
    
    response = requests.post(url, json=payload)
    
    print(f"Telegram 狀態碼: {response.status_code}")
    print(f"Telegram 回應內容: {response.text}")

if __name__ == "__main__":
    print("正在處理今日新聞...")
    news_data = get_news_content()
    article = generate_social_post(news_data)
    send_to_telegram(article)
    print("程式執行完畢！")
