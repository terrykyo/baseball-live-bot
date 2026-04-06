import os
import time
import datetime
import logging
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('cpbl_bot')

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class CPBLBot:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.last_games_data = []
        self.last_date_str = ""

    def send_telegram_message(self, text):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram Bot Token or Chat ID not configured. Message: " + text)
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("Telegram notification sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def scrape_today_games(self):
        logger.info("Starting Playwright to scrape CPBL schedule...")
        games = []
        today = datetime.date.today()
        day_str = str(today.day).zfill(2)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://www.cpbl.com.tw/schedule")
                page.wait_for_selector(".date", timeout=20000)
                time.sleep(2) 

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                date_divs = soup.find_all('div', class_='date')
                today_div = None
                for d in date_divs:
                    if d.get('data-date') == day_str or d.text.strip() == day_str or d.text.strip() == str(today.day):
                        today_div = d
                        break
                
                if today_div and today_div.parent:
                    game_divs = today_div.parent.find_all('div', class_=lambda c: c and 'game' in c.lower() and 'game_no' not in c.lower())
                    for g in game_divs:
                        text_content = g.text.strip()
                        if not text_content:
                            continue
                            
                        items = [line.strip() for line in text_content.split('\n') if line.strip()]
                        if len(items) >= 4:
                            stadium = items[0]
                            time_str = items[-1]
                            matchup = " ".join(items[1:-1])
                            games.append({
                                'stadium': stadium,
                                'matchup': matchup.replace('VS.', 'vs'),
                                'time': time_str
                            })
                browser.close()
                return games
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return None # Returning None indicates an error, so we don't clear state

    def diff_and_notify(self, old_games, new_games, today_str):
        # 換日邏輯：自動推播全新一天的總表
        if self.last_date_str != today_str:
            if not new_games:
                msg = f"📅 <b>{today_str} 中職賽程</b>\n今日無一軍例行賽。"
                self.send_telegram_message(msg)
            else:
                msg_lines = [f"📅 <b>{today_str} 中職賽程</b>"]
                for g in new_games:
                    msg_lines.append(f"⚾ {g['time']} {g['matchup']} @ {g['stadium']}")
                self.send_telegram_message("\n".join(msg_lines))
            return

        # 比對同日內的資料差異 (比分更新、狀態改變等)
        for new_g in new_games:
            # 用場地來對應同一場比賽 (因為每天一個場地通常只有一場)
            old_g = next((g for g in old_games if g['stadium'] == new_g['stadium']), None)
            
            if not old_g:
                continue
                
            # 若時間狀態或對戰比分字串改變
            if old_g['time'] != new_g['time'] or old_g['matchup'] != new_g['matchup']:
                msg = f"🔥 <b>賽況更新</b>\n⚾ {new_g['matchup']}\n📍 {new_g['stadium']} [{new_g['time']}]"
                self.send_telegram_message(msg)
                logger.info(f"Update sent for {new_g['stadium']}: {new_g['matchup']} [{new_g['time']}]")

    def polling_task(self):
        logger.info("Polling for CPBL Schedule updates...")
        games = self.scrape_today_games()
        if games is None: # Scraper failed this minute
            logger.warning("Scraping returned None, skipping diff this minute.")
            return

        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        # 判斷差異並執行通知 (如果是程式剛啟動，last_date_str 為空，此處會觸發換日邏輯)
        self.diff_and_notify(self.last_games_data, games, today_str)

        # 更新狀態快取
        self.last_games_data = games
        self.last_date_str = today_str

    def start(self):
        # 設定為每一分鐘輪詢一次
        self.scheduler.add_job(self.polling_task, trigger=CronTrigger(minute='*'))
        self.scheduler.start()
        logger.info("CPBL Live Polling Bot Started. Executing immediate initial payload...")
        
        # 啟動時立刻執行一次，把初始狀態抓下來並推播每日課表
        self.polling_task()
        
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()

if __name__ == '__main__':
    bot = CPBLBot()
    bot.start()
