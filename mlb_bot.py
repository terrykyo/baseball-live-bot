import os
import time
import datetime
import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('mlb_bot')

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class MLBBot:
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

    def fetch_today_games(self):
        logger.info("Fetching MLB schedule from statsapi...")
        games_list = []
        # We can pass ?sportId=1 to get MLB. It defaults to the current MLB daily schedule.
        # Alternatively, we can force today's date in Taipei time, but MLB handles its own day rollovers best without params.
        # For safety across timezones, let's grab the actual schedule for the current date in US Eastern Time or just Taipei Time.
        # Actually `sportId=1` dynamically returns today's games in the US.
        api_url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        
        try:
            # Adding headers just to be polite to the API
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(api_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            dates = data.get("dates", [])
            if not dates:
                return []
                
            # Usually the first object in 'dates' holds the games for the current active schedule day
            today_date_str = dates[0].get("date", "")
            raw_games = dates[0].get("games", [])
            
            for g in raw_games:
                game_pk = g.get("gamePk")
                status = g.get("status", {}).get("detailedState", "Unknown")
                
                teams = g.get("teams", {})
                away_team = teams.get("away", {}).get("team", {}).get("name", "Unknown Away")
                away_score = teams.get("away", {}).get("score", 0) # Defaults to 0 if not started
                
                home_team = teams.get("home", {}).get("team", {}).get("name", "Unknown Home")
                home_score = teams.get("home", {}).get("score", 0)
                
                venue = g.get("venue", {}).get("name", "Unknown Venue")
                
                # Format game Date (it is in UTC) e.g., "2026-03-30T20:10:00Z"
                utc_time_str = g.get("gameDate", "")
                local_time_str = "TBD"
                if utc_time_str:
                    try:
                        # Parse UTC ISO-8601
                        dt_utc = datetime.datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
                        # Convert to Taiwan Time (UTC+8)
                        dt_local = dt_utc + datetime.timedelta(hours=8)
                        local_time_str = dt_local.strftime("%H:%M")
                    except Exception:
                        local_time_str = utc_time_str

                # Combine into our standard dictionary
                # Use standard formats
                if status in ("Scheduled", "Pre-Game", "Postponed", "Delayed Start", "Warmup"):
                    score_str = f"{away_team} vs {home_team}"
                else:
                    score_str = f"{away_team} {away_score} : {home_score} {home_team}"
                
                games_list.append({
                    'id': game_pk,
                    'stadium': venue,
                    'matchup': score_str,
                    'time': local_time_str,
                    'status': status,
                    'date': today_date_str
                })
                
            return games_list
        except Exception as e:
            logger.error(f"Error fetching MLB games: {e}")
            return None

    def diff_and_notify(self, old_games, new_games):
        if not new_games:
            return

        today_str = new_games[0]['date']

        # 換日邏輯：自動推播全新一天的總表
        if self.last_date_str != today_str:
            msg_lines = [f"📅 <b>MLB 賽程總表 ({today_str})</b>"]
            for g in new_games:
                # E.g., ⚾ 08:05 Los Angeles Dodgers vs New York Yankees @ Yankee Stadium
                msg_lines.append(f"⚾ {g['time']} {g['matchup']} @ {g['stadium']}")
            self.send_telegram_message("\n".join(msg_lines))
            return

        # 比對同日內的資料差異
        for new_g in new_games:
            # Find the old game by its unique gamePk
            old_g = next((g for g in old_games if g['id'] == new_g['id']), None)
            
            if not old_g:
                continue
                
            # If the score changes OR the status changes
            if old_g['matchup'] != new_g['matchup'] or old_g['status'] != new_g['status']:
                # Translate status to Chinese if possible, else use raw
                status_tw = new_g['status']
                if status_tw == "In Progress":
                    status_tw = "比賽中"
                elif status_tw == "Final":
                    status_tw = "比賽結束"
                elif status_tw == "Delayed":
                    status_tw = "因雨延遲"
                elif status_tw == "Warmup":
                    status_tw = "熱身中"

                msg = f"🇺🇸🔥 <b>MLB 即時戰報 ({status_tw})</b>\n⚾ {new_g['matchup']}\n📍 {new_g['stadium']}"
                self.send_telegram_message(msg)
                logger.info(f"Update sent for {new_g['id']}: {new_g['matchup']} [{new_g['status']}]")

    def polling_task(self):
        logger.info("Polling for MLB Schedule updates...")
        games = self.fetch_today_games()
        if games is None:
            logger.warning("Fetching returned None, skipping diff this minute.")
            return

        if not games:
            # If dates array is empty (no games today)
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            if self.last_date_str != today_str:
                self.send_telegram_message(f"📅 <b>MLB 賽程總表 ({today_str})</b>\n今日無大聯盟賽事。")
                self.last_date_str = today_str
            return

        today_str = games[0]['date']
        
        # 判斷差異並執行通知 (如果是程式剛啟動，last_date_str 為空，此處會觸發換日邏輯)
        self.diff_and_notify(self.last_games_data, games)

        # 更新狀態快取
        self.last_games_data = games
        self.last_date_str = today_str

    def start(self):
        # 設定為每一分鐘輪詢一次
        self.scheduler.add_job(self.polling_task, trigger=CronTrigger(minute='*'))
        self.scheduler.start()
        logger.info("MLB Live Polling Bot Started. Executing immediate initial payload...")
        
        # 啟動時立刻執行一次，把初始狀態抓下來並推播每日課表
        self.polling_task()
        
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()

if __name__ == '__main__':
    bot = MLBBot()
    bot.start()
