# Auto Gifts Buyer Bot

![App Demo](PLACEHOLDER_FOR_GIF_HERE)

## 📌 Project Overview

This project is a comprehensive solution designed to purchase Telegram Stars and Premium subscriptions at rates cheaper than the built-in Telegram app offers, utilizing the Fragment API. Additionally, it features a specialized autonomous script capable of monitoring and purchasing unique, limited-edition Telegram gifts as soon as they become available.

The system is built with a microservices-inspired architecture, separating the user-facing Telegram bot from the core purchasing logic and the autonomous gifts buyer.

## 🚀 Features

*   **Discounted Purchases**: Buy Telegram Stars and Premium subscriptions cheaper than official in-app prices via direct Fragment API integration.
*   **Unique Gifts Autopilot**: A dedicated script (`buy-gifts-service`) that monitors for new limited-edition gifts and automatically attempts to purchase them based on configurable limits.
*   **Automated Billing**: Handles invoices, payments (TON/USDT), and order fulfillment automatically.
*   **User Management**: Tracks user balances, referral bonuses, and purchase history via MongoDB.
*   **Admin Tools**: Includes functionality for managing bot accounts and viewing order statistics.

## 🛠 Technologies Used

*   **Language**: [Python 3.12](https://www.python.org/)
*   **Bot Framework**: [Aiogram 3.x](https://docs.aiogram.dev/) (Asynchronous framework for Telegram Bot API)
*   **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (For internal APIs and webhooks)
*   **Database**: [MongoDB](https://www.mongodb.com/) (using [Motor](https://motor.readthedocs.io/) driver for async access)
*   **Telegram Client**: [Pyrogram](https://docs.pyrogram.org/) (For userbot functionality and interacting with Telegram API)
*   **HTTP Client**: [Aiohttp](https://docs.aiohttp.org/)
*   **Containerization**: Docker (optional, files provided)

## 📂 Project Structure

The project is organized into several key modules:

*   **`main_bot/`**: The primary user-facing Telegram bot. Handles user interaction, payments, and commands.
*   **`fragment_purchase/`**: A service responsible for interacting with the Fragment API to execute purchases (Stars/Premium).
*   **`buy-gifts-service/`**: An independent script that monitors specific channels or signals to buy unique gifts instantly.
*   **`deposit-receiver/`**: (Assumed) Service to monitor blockchain transactions for incoming deposits.
*   **`bot_account_manager/`**: Utilities for managing bot accounts.

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed:

*   Python 3.9+
*   MongoDB (Running locally or a cloud instance like MongoDB Atlas)
*   Telegram API Credentials (`API_ID` and `API_HASH`)
*   Telegram Bot Token via [@BotFather](https://t.me/BotFather)

## 📥 Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd auto-gifts-buyer-bot
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may also need to install specific dependencies for sub-modules if not covered in the root `requirements.txt`.*

## 🔧 Configuration

You need to configure the environment variables and configuration files for each service.

### 1. Main Bot Configuration (`main_bot/config.py`)

Open `main_bot/config.py` and update the following values:

*   `API_ID` & `API_HASH`: Get these from [my.telegram.org](https://my.telegram.org).
*   `BOT_TOKEN`: Your Telegram Bot Token.
*   `MONGO_URI`: Connection string to your MongoDB instance.
*   `DB_NAME`: Database name (default is "gifts").

### 2. Fragment Service Configuration (`fragment_purchase/config.py`)

**⚠️ IMPORTANT:** This file deals with sensitive purchase data.

Open `fragment_purchase/config.py` and configure:
*   `MNEMONICS`: The seed phrase for the wallet used to make purchases.
*   `API_KEY` & `FRAGMENT_HASH`: Keys required for Fragment API access.
*   `FRAGMENT_COOKIES`: Active session cookies for Fragment.com.

### 3. Gifts Service (`buy-gifts-service/main.py`)

Update the `API_ID` and `API_HASH` variables directly in `buy-gifts-service/main.py` if they are hardcoded there.

## 🏃‍♂️ Running Locally

To run the full system locally, you need to start the services in separate terminal windows.

### Step 1: Start MongoDB
Ensure your MongoDB instance is running.

### Step 2: Start the Fragment Purchase Service
This service handles the actual purchasing logic.
```bash
cd fragment_purchase
python3 app.py
```
*Runs on port 8000 by default.*

### Step 3: Start the Main Bot
**Note:** If running locally, ensure `main_bot/utils/buy_stars_premium.py` points to your local Fragment service URL (e.g., `http://localhost:8000`) instead of the production `fly.dev` URL.

```bash
cd main_bot
python3 main.py
```
*Runs on port 8001 by default.*

### Step 4: Run the Gifts Buyer Script
This script runs independently to snipe gifts.
```bash
cd buy-gifts-service
python3 main.py
```

## ⚠️ Disclaimer

This project involves financial transactions (purchasing Telegram assets). Use at your own risk.
*   **Security**: Never share your `MNEMONICS` or `session` files.
*   **TOS**: innovative automation of Telegram features may be subject to Telegram's Terms of Service.
