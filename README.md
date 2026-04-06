# ⚾ Baseball Live Polling Bot (CPBL & MLB)

[🇹🇼 繁體中文](#繁體中文-traditional-chinese) | [🇺🇸 English](#english)

---

## 🇹🇼 繁體中文 (Traditional Chinese)

這是一個雙引擎的 Telegram 自動賽況通報系統。專為喜愛台灣中華職棒 (CPBL) 以及美國職棒大聯盟 (MLB) 的球迷所設計。

將機器人掛載在背景，它就會以每一分鐘的頻率進行**「智慧輪詢 (Live Polling)」**，並內建差異比對引擎（Diff Engine）。只要發生 **比分變化**、**比賽開打**、**賽事延期** 或 **比賽結束**，您的 Telegram 就能在第一時間收到即時推播，其餘時間則保持最高品質的靜默。

### ✨ 專案特色與架構

本專案同時包含了兩支獨立運作的爬蟲腳本，因應兩個聯盟截然不同的官網架構：

*   **🇹🇼 中職版 (`cpbl_bot.py`) - Playwright 霸氣爬蟲**  
    中職官網賽程表為了阻擋爬蟲，採用了嚴格的 CSRF Token 與 JS 動態渲染。我們採用最穩定的解法：利用 `Playwright` 無頭瀏覽器在背景載入真實 DOM，再交由 `BeautifulSoup` 硬核解譯出賽程與即時比分。
*   **🇺🇸 大聯盟版 (`mlb_bot.py`) - StatsAPI 輕盈解法**  
    大聯盟官方非常友善地開放了全球公用的即時 JSON API (`statsapi.mlb.com`)。因此我們捨棄了笨重的瀏覽器，僅透過原生的 `requests` 以純數據流的方式解析賽事，不僅能精準捕捉 "In Progress", "Postponed", "Delayed" 等多重狀態，更幾乎不消耗任何本機 CPU 效能。

### 💻 本地端部署教學 (How to Use)

#### 1. 安裝套件
確保您的系統已經安裝 Python 3.8 以上版本。接著安裝本專案所需的所有相依套件：
```bash
pip install -r requirements.txt
playwright install chromium
```

#### 2. 設定環境變數
將本資料夾內的 `.env.example` 重新命名為 `.env`，並填入您申請到的 Telegram Bot 憑證資訊：
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

#### 3. 設定 Python 路徑 (視需調整)
由於 Windows 系統的複雜性，本專案提供了快速啟動檔 `start_cpbl_bot.bat` 與 `start_mlb_bot.bat`。
👉 **重要**：請右鍵編輯這兩個 `.bat` 啟動檔，將裡面的 `"C:\Users\...\python.exe"` 替換成您個人電腦上實際安裝的 Python 絕對路徑。

#### 4. 雙擊即啟動
改好正確的 Python 環境路徑後，**分別點擊兩下執行**這兩支 `.bat` 檔，當出現低調的黑色指令視窗時，機器人便已經正式上工。您可以同時開啟中職與大聯盟的視窗！

---

## 🇺🇸 English

A dual-engine Telegram automated live-scoring bot tailored for baseball fans tracking the **Taiwanese CPBL** (Chinese Professional Baseball League) and the **American MLB** (Major League Baseball).

Running silently in the background, the bot utilizes a **1-minute Live Polling** mechanism hooked to a custom Diff Engine. You will receive an instant Telegram push notification every time a game **starts, ends, gets postponed**, or whenever **the score updates**.

### ✨ Features & Architecture

This repository contains two independently operating spider scripts to tackle the distinctly different architectures of the respective official websites:

*   **🇹🇼 CPBL Version (`cpbl_bot.py`) - The Playwright Approach**  
    To bypass the strict CSRF tokens and server-side JS rendering logic of the CPBL official schedule, we deployed a headless Chromium instance via `Playwright` to simulate a real browser, coupled with `BeautifulSoup` to accurately parse the rendered DOM structure.
*   **🇺🇸 MLB Version (`mlb_bot.py`) - The StatsAPI Approach**  
    Major League Baseball generously provides a universally accessible real-time JSON API (`statsapi.mlb.com`). Taking advantage of this, `mlb_bot.py` completely ditches browser simulation and instead processes pure data streams using lightweight `requests`. This method accurately detects fine-grained game states (e.g., In Progress, Postponed) while keeping CPU usage virtually at zero.

### 💻 Local Deployment (How to Use)

#### 1. Install Dependencies
Ensure you have Python 3.8+ installed, then install the required dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

#### 2. Configure Environment Variables
Rename `.env.example` to `.env` and fill in your Telegram Bot credentials:
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

#### 3. Configure Python Path (Windows)
For convenience, `.bat` launcher files are provided for Windows users (`start_cpbl_bot.bat` & `start_mlb_bot.bat`). 
👉 **Important**: Right-click to edit these `.bat` files and replace the dummy `"C:\Users\...\python.exe"` path with the absolute path of your local Python executable.

#### 4. Launch!
Once the Python path is set correctly, simply **double-click** the `.bat` files. A command prompt window will pop up indicating that the bot is now actively polling. You can run both bots simultaneously to track games halfway across the globe!
