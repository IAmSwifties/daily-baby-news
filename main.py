import os
import time
import requests
from google import genai
from datetime import datetime
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import base64
import re

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def decode_google_news_url(url):
    """底層破解：直接將 Google URL 裡的 Base64 payload 解碼，取出真實連結"""
    try:
        if '/articles/' in url:
            # 擷取 /articles/ 後面的加密字串
            encoded_str = url.split('/articles/')[1].split('?')[0]
            # 補齊 Base64 結尾需要的 '=' 符號
            encoded_str += "=" * ((4 - len(encoded_str) % 4) % 4)
            # 使用 URL-safe 模式解碼成二進位資料
            decoded_bytes = base64.urlsafe_b64decode(encoded_str)
            # 從二進位資料中，利用正則表達式精準捕捉 http 開頭的真實網址
            match = re.search(rb'https?://[^\x00-\x1F"\'<>\s]+', decoded_bytes)
            if match:
                return match.group(0).decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ 本地解碼失敗: {e}")
    # 如果解碼失敗，就退回原本的網址
    return url

def get_news_content():
    print("開始搜尋 Google 新聞並抓取內文...")
    keywords = '育兒 新聞'
    query = urllib.parse.quote(f"{keywords} when:1d")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        print(f"👉 Google 回傳了 {len(items)} 篇新聞標題")
        
        news_data_list = []
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        for item in items:
            title = item.find('title').text
            google_link = item.find('link').text
            clean_title = title.split(' - ')[0] if ' - ' in title else title
            
            print(f"\n正在處理: {clean_title[:20]}...")
            
            # 【大絕招】不連線，直接在程式裡把隱藏的網址解算出來！
            real_link = decode_google_news_url(google_link)
            
            if real_link != google_link:
                print(f"  🔗 成功解出真實網址！直接前往目標伺服器...")
            else:
                print("  ⚠️ 無法解出真實網址，嘗試硬闖...")
                
            try:
                # 直接連線到真正的新聞網站
                article_req = session.get(real_link, headers=headers, timeout=10)
                soup = BeautifulSoup(article_req.content, 'html.parser')
                
                paragraphs = soup.find_all('p')
                content_list = [p.text.strip() for p in paragraphs if p.text.strip()]
                full_content = " ".join(content_list)
                content = full_content[:1500]
                
                if len(content) > 50: 
                    news_data_list.append(f"【標題】：{clean_title}\n【內容】：{content}...\n【連結】：{real_link}\n")
                    print("  ✅ 成功抓回真實內文封包！")
                else:
                    print("  ⚠️ 目標網頁內無足夠的文字段落。")
                    
            except Exception as e:
                print(f"  ❌ 抓取目標伺服器失敗：{e}")
            
            # 抓滿 3 篇有內文的新聞就好
            if len(news_data_list) >= 3:
                break
                
        if news_data_list:
            final_news = "\n".join(news_data_list)
            print("\n新聞數據擷取完成！準備交給 AI...")
            return final_news
        else:
            return "今天沒有抓到相關新聞內文喔！"
            
    except Exception as e:
        print(f"系統發生錯誤: {e}")
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
    print("正在啟動今日新聞處理程序...")
    news_data = get_news_content()
    
    if "沒有抓到" not in news_data and "無法取得" not in news_data:
        article = generate_social_post(news_data)
        send_to_telegram(article)
    else:
        send_to_telegram(news_data)
        
    print("程序執行完畢！")
