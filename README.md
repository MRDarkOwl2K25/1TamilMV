
---

# **Tamil Blasters RSS Bot**

**TamilMV RSS Bot** is an advanced Telegram bot designed to automatically post torrent files from [1TamilMV](https://www.1tamilmv.blue) to a specified Telegram channel. The bot performs periodic checks to ensure the latest torrents are fetched and posted seamlessly.

---

## **Features**

- 🚀 **Automatic Torrent Fetching**: Scrapes torrent files from 1TamilMV and posts them to a Telegram channel.
- 🛠️ **Flask Health Check**: Includes a lightweight Flask server to monitor the bot's health.
- 🔄 **Threaded Flask Server**: Ensures the Flask server runs in a separate thread, preventing any interference with the bot's core functionality.
- ☁️ **Cloud Deployment Ready**: Compatible with platforms like [Koyeb](https://www.koyeb.com), [Render](https://render.com), and [Heroku](https://heroku.com).

---

## **Requirements**

### **Python Libraries**
Install the required libraries by running the following command:
```bash
pip install -r requirements.txt
```

---

## **Configuration**

### **Environment Variables**

The bot requires the following environment variables to be set:

1. **TOKEN**: Your Telegram Bot token from [@BotFather](https://t.me/BotFather)
2. **API_ID**: Your Telegram API ID from [my.telegram.org](https://my.telegram.org)
3. **API_HASH**: Your Telegram API Hash from [my.telegram.org](https://my.telegram.org)
4. **OWNER**: Your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot))
5. **CHANNEL_ID**: The Telegram channel ID where torrents will be posted (numeric ID, negative for channels)
6. **PORT**: Port for the web server (default: 8000)

**Note**: The variable names are case-sensitive and must match exactly as shown above.

### **Setting Up Environment Variables**

#### **Local Development**
1. Copy `env_template.txt` to `.env`:
   ```bash
   cp env_template.txt .env
   ```
2. Edit `.env` and fill in your actual values:
   ```env
   TOKEN=your_bot_token_here
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here
   OWNER=your_user_id_here
   CHANNEL_ID=your_channel_id_here
   PORT=8000
   ```

#### **Cloud Deployment**
When deploying to cloud platforms, add these environment variables in your service configuration:

- **Koyeb**: Add in the Environment Variables section
- **Render**: Add in the Environment Variables section  
- **Heroku**: Use `app.json` for automatic configuration

---

## **How to Run**

### **Local Environment**

1. Clone the repository:
    ```bash
    git clone https://github.com/mntg4u/assistent.git
    cd Tamil-Blasters-Rss-Bot-main
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables (see Configuration section above)

4. Run the bot:
    ```bash
    python bot.py
    ```

### **Deployment**

#### **Heroku**
1. The `app.json` file is already configured for Heroku deployment
2. Simply connect your GitHub repository to Heroku
3. All required environment variables will be prompted during deployment

#### **Koyeb**

1. Log in to [Koyeb](https://www.koyeb.com).
2. Create a new service and link it to your GitHub repository.
3. Add all required environment variables in the service configuration:
   - `TOKEN`
   - `API_ID`
   - `API_HASH`
   - `OWNER`
   - `CHANNEL_ID`
   - `PORT` (optional, defaults to 8000)
4. Deploy the service.

#### **Render**

1. Log in to [Render](https://render.com).
2. Create a new web service and connect it to your GitHub repository.
3. Add the necessary environment variables:
   - `TOKEN`
   - `API_ID`
   - `API_HASH`
   - `OWNER`
   - `CHANNEL_ID`
   - `PORT` (optional, defaults to 8000)
4. Set the Start Command to:
    ```bash
    python bot.py
    ```
5. Deploy the service.

---

## **Notes**

- The bot requires **valid Telegram API credentials** to function.
- Ensure the target Telegram channel allows the bot to post messages.
- The bot performs periodic checks every **15 minutes** to fetch and post new torrents.
- Make sure your bot has admin privileges in the target channel.

---

## **License**

This project is licensed under the **MIT License**. Feel free to use, modify, and distribute it as per the terms of the license.

---

