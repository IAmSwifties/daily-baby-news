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
        
        # 1. 建立 Session，並加上更完整的瀏覽器偽裝（騙過伺服器）
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        for item in items:
            title = item.find('title').text
            google_link = item.find('link').text
            
            # 把新聞來源的名字去掉，讓標題乾淨一點
            clean_title = title.split(' - ')[0] if ' - ' in title else title
            print(f"正在破解並讀取: {clean_title[:20]}...")
            
            try:
                # 2. 先連到 Google 的中繼站
                mid_req = session.get(google_link, headers=headers, timeout=10)
                mid_soup = BeautifulSoup(mid_req.content, 'html.parser')
                
                # 3. 破解轉址：找出真正的網址 (Google 通常會有一個 a 標籤包著真實網址)
                real_link = google_link
                a_tag = mid_soup.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    real_link = a_tag['href']
                    print("  🔗 破解中繼站成功，前往真實網頁抓取...")
                    
                    # 4. 連到真正的網站抓新聞內文
                    article_req = session.get(real_link, headers=headers, timeout=10)
                    soup = BeautifulSoup(article_req.content, 'html.parser')
                    
                    paragraphs = soup.find_all('p')
                    content_list = [p.text.strip() for p in paragraphs if p.text.strip()]
                    full_content = " ".join(content_list)
                    content = full_content[:1500]
                    
                    if len(content) > 50: 
                        news_data_list.append(f"【標題】：{clean_title}\n【內容】：{content}...\n【連結】：{real_link}\n")
                        print("  ✅ 成功抓到真實內文！")
                    else:
                        print("  ⚠️ 網頁內沒有足夠的文字 (可能都是圖片或影片)。")
                else:
                    print("  ⚠️ 破解轉址失敗，找不到真實連結。")
                    
            except Exception as e:
                print(f"  ❌ 抓取失敗：{e}")
            
            # 抓滿 3 篇有內文的新聞就收工，避免 AI 負載過大
            if len(news_data_list) >= 3:
                break
                
        if news_data_list:
            final_news = "\n".join(news_data_list)
            print("新聞抓取完成！準備交給 AI...")
            return final_news
        else:
            return "今天沒有抓到相關新聞內文喔！"
            
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
