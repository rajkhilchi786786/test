import os
import logging
import sqlite3
import uuid
import random
import string
import time
import json
import requests
import asyncio
from datetime import datetime
from functools import wraps
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

# ---------------------------
# ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ
# ---------------------------
BOT_TOKEN = os.getenv("CLOUDWAYS_BOT_TOKEN") or "7668443193:AAEH9QeB5fZ4UeNw_SGkeB_dT8pHwv8YN68"
ADMIN_IDS = [7996314470, 7147401720]
REQUIRED_CHANNELS = ["@ItsMeVishalSupport", "@anniemusicsupport"]

DB_PATH = "cloudways_bot.db"
DEFAULT_CREDITS = 10

CLOUDWAYS_SIGNUP_API = "https://api.cloudways.com/api/v2/guest/signup"

# ---------------------------
# ʟᴏɢɢɪɴɢ
# ---------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("cloudways_bot")

# ---------------------------
# ᴜᴛɪʟɪᴛʏ: ʀᴜɴ ʙʟᴏᴄᴋɪɴɢ ɪɴ ᴇxᴇᴄᴜᴛᴏʀ
# ---------------------------
def ᴠɪꜱʜᴀʟ_ʀᴜɴ_ʙʟᴏᴄᴋɪɴɢ(func):
    @wraps(func)
    async def ᴠɪꜱʜᴀʟ_ᴡʀᴀᴘᴘᴇʀ(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return ᴠɪꜱʜᴀʟ_ᴡʀᴀᴘᴘᴇʀ

# ---------------------------
# ʙᴏᴛ ᴄʟᴀꜱꜱ
# ---------------------------
class ᴄʟᴏᴜᴅᴡᴀʏꜱʙᴏᴛ:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ᴠɪꜱʜᴀʟ_ᴇɴꜱᴜʀᴇ_ᴅʙ()

    def _ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ᴠɪꜱʜᴀʟ_ᴇɴꜱᴜʀᴇ_ᴅʙ(self):
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT {DEFAULT_CREDITS},
                used INTEGER DEFAULT 0,
                last_request TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                password TEXT,
                first_name TEXT,
                last_name TEXT,
                status TEXT,
                risk_score INTEGER,
                verification_sent BOOLEAN,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                cloudways_response TEXT
            )
        """)
        conn.commit()
        conn.close()

    # ---------------------------
    # ᴄʜᴀɴɴᴇʟ ᴍᴇᴍʙᴇʀꜱʜɪᴘ ᴄʜᴇᴄᴋ
    # ---------------------------
    async def _ᴠɪꜱʜᴀʟ_ᴄʜᴇᴄᴋ_ᴄʜᴀɴɴᴇʟ_ᴍᴇᴍʙᴇʀꜱʜɪᴘ(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        try:
            for channel in REQUIRED_CHANNELS:
                member = await context.bot.get_chat_member(channel, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            return True
        except Exception:
            return False

    # ---------------------------
    # ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴍᴀɴᴅ
    # ---------------------------
    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ʙʀᴏᴀᴅᴄᴀꜱᴛ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
            return
            
        if not context.args:
            await update.message.reply_text("📝 Usage: /broadcast your message here")
            return
            
        message = " ".join(context.args)
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()
        conn.close()
        
        success = 0
        failed = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **Broadcast** 📢\n\n{message}"
                )
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.1)
            
        await update.message.reply_text(f"📨 Broadcast results:\n✅ Success: {success}\n❌ Failed: {failed}")

    # ---------------------------
    # ᴜꜱᴇʀ & ᴄʀᴇᴅɪᴛꜱ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ᴀᴅᴅ_ᴜꜱᴇʀ_ɪꜰ_ᴍɪꜱꜱɪɴɢ(self, user_id: int, username: str):
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id, username, credits, used) VALUES (?, ?, ?, ?)",
                    (user_id, username, DEFAULT_CREDITS, 0))
        conn.commit()
        conn.close()

    def ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(self, user_id: int) -> int:
        if user_id in ADMIN_IDS:
            return 99999999
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("SELECT credits, used FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return 0
        return max(0, row["credits"] - row["used"])

    def ᴠɪꜱʜᴀʟ_ᴛʀʏ_ᴄᴏɴꜱᴜᴍᴇ_ᴄʀᴇᴅɪᴛ(self, user_id: int, amount: int = 1) -> bool:
        if user_id in ADMIN_IDS:
            return True
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET used = used + ?, last_request = ?
            WHERE user_id = ? AND used + ? <= credits
        """, (amount, datetime.utcnow().isoformat(), user_id, amount))
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        return updated

    def ᴠɪꜱʜᴀʟ_ʀᴇꜰᴜɴᴅ_ᴄʀᴇᴅɪᴛ(self, user_id: int, amount: int = 1):
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("UPDATE users SET used = used - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    # ---------------------------
    # ᴀᴄᴄᴏᴜɴᴛ ᴘᴇʀꜱɪꜱᴛᴇɴᴄᴇ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ꜱᴀᴠᴇ_ᴀᴄᴄᴏᴜɴᴛ(self, user_id: int, details: Dict[str, Any], result: Dict[str, Any], cloudways_response: str = ""):
        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO accounts (email, password, first_name, last_name, status, risk_score, verification_sent, user_id, cloudways_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            details.get("email"),
            details.get("password"),
            details.get("first_name"),
            details.get("last_name"),
            result.get("status", ""),
            int(result.get("risk_score", 0) or 0),
            1 if result.get("verification_sent") else 0,
            user_id,
            cloudways_response
        ))
        conn.commit()
        conn.close()

    # ---------------------------
    # ʀᴀɴᴅᴏᴍ ᴜꜱᴇʀ ɢᴇɴᴇʀᴀᴛᴏʀ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ʀᴀɴᴅᴏᴍ_ᴜꜱᴇʀ_ᴅᴇᴛᴀɪʟꜱ(self, email: str):
        try:
            r = requests.get("https://randomuser.me/api/?nat=us", timeout=8)
            r.raise_for_status()
            data = r.json()["results"][0]["name"]
            first = data["first"].capitalize()
            last = data["last"].capitalize()
        except Exception:
            first = random.choice(["John", "Vishalpapa", "Rajpapa", "Mike", "Alex", "David", "Sarah", "Emma"])
            last = random.choice(["Smith", "Brown", "Jones", "Patel", "Kumar"])
        
        password_base = random.choice(["Vishal", "Rajowner"])
        password = f"{password_base}@{random.randint(1000,9999)}"
        
        return {"first_name": first, "last_name": last, "email": email, "password": password}

    # ---------------------------
    # ᴀᴅᴠᴀɴᴄᴇᴅ ᴅᴇᴠɪᴄᴇ ꜰɪɴɢᴇʀᴘʀɪɴᴛ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ᴅᴇᴠɪᴄᴇ_ꜰɪɴɢᴇʀᴘʀɪɴᴛ(self):
        device_id = str(uuid.uuid4())
        
        # ᴀᴅᴠᴀɴᴄᴇᴅ ᴛᴀʟᴏɴ ᴅᴀᴛᴀ
        talon = {
            "device_id": ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)),
            "session_id": str(uuid.uuid4()),
            "os": random.choice(["Android 14","iOS 17","Windows 11","macOS 14"]),
            "os_build": f"{random.randint(10000,99999)}.{random.randint(10,99)}",
            "cpu": random.choice(["Snapdragon 8 Gen 2","Apple A17","Intel i7-12700K","M2 Pro"]),
            "gpu": random.choice(["Adreno 740","Apple GPU","NVIDIA RTX 4080"]),
            "ram": f"{random.choice([4,6,8,12,16,32])}GB",
            "storage": f"{random.choice([64,128,256,512])}GB",
            "lang": random.choice(["en-US","en-GB","hi-IN"]),
            "timezone": "+05:30",
            "battery_level": random.randint(20, 95),
            "charging": random.choice([True, False]),
            "screen": f"{random.choice([1080,1440,1920])}x{random.choice([1920,2160])}",
            "device_model": random.choice(["Pixel 7 Pro","iPhone 14 Pro","Samsung S23 Ultra","OnePlus 11"]),
            "network": random.choice(["WiFi","4G","5G"]),
            "browser": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ]),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "build_number": ''.join(random.choices(string.ascii_letters + string.digits, k=10)),
            "app_version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
            "device_country": random.choice(["US","IN","GB","CA","AU"]),
            "device_language": random.choice(["en","hi","es","fr"]),
            "device_timezone": random.choice(["Asia/Kolkata","America/New_York","Europe/London"]),
            "screen_density": random.choice([2.0, 3.0, 2.5, 3.5]),
            "font_scale": random.choice([1.0, 1.1, 0.9, 1.2]),
        }
        return device_id, talon

    # ---------------------------
    # ꜱɪɢɴᴜᴘ ʀᴇQᴜᴇꜱᴛ (ʙʟᴏᴄᴋɪɴɢ)
    # ---------------------------
    def _ᴠɪꜱʜᴀʟ_ꜱɪɢɴᴜᴘ_ʀᴇQᴜᴇꜱᴛ_ʙʟᴏᴄᴋɪɴɢ(self, details: Dict[str, str]) -> Dict[str, Any]:
        """
        ᴘᴇʀꜰᴏʀᴍ ᴀ ʙʟᴏᴄᴋɪɴɢ ʜᴛᴛᴘ ᴘᴏꜱᴛ ᴛᴏ ᴄʟᴏᴜᴅᴡᴀʏꜱ ꜱɪɢɴᴜᴘ ᴇɴᴅᴘᴏɪɴᴛ.
        ʀᴇᴛᴜʀɴꜱ ᴘᴀʀꜱᴇᴅ ᴊꜱᴏɴ ᴏʀ ᴀɴ ᴇʀʀᴏʀ ᴅɪᴄᴛ.
        """
        try:
            device_id, talon = self.ᴠɪꜱʜᴀʟ_ᴅᴇᴠɪᴄᴇ_ꜰɪɴɢᴇʀᴘʀɪɴᴛ()
            payload = {
                "first_name": details["first_name"],
                "last_name": details["last_name"],
                "email": details["email"],
                "password": details["password"],
                "gdpr_consent": True,
                "promo_code": "",
                "persona_tag_id": 13,
                "signup_price_id": "b",
                "talonData": talon,
                "user_unique_id": str(uuid.uuid4()),
                "signup_page_template_id": 0
            }
            headers = {
                "User-Agent": talon["browser"],
                "Content-Type": "application/json",
                "x-device-id": device_id
            }
            resp = requests.post(CLOUDWAYS_SIGNUP_API, json=payload, headers=headers, timeout=20)
            try:
                response_data = resp.json()
                return {"success": True, "data": response_data, "status_code": resp.status_code}
            except ValueError:
                return {"success": False, "error": f"Non-JSON response: {resp.status_code}", "raw": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e), "status_code": 0}

    @ᴠɪꜱʜᴀʟ_ʀᴜɴ_ʙʟᴏᴄᴋɪɴɢ
    def ᴠɪꜱʜᴀʟ_ꜱɪɢɴᴜᴘ_ʀᴇQᴜᴇꜱᴛ(self, details):
        return self._ᴠɪꜱʜᴀʟ_ꜱɪɢɴᴜᴘ_ʀᴇQᴜᴇꜱᴛ_ʙʟᴏᴄᴋɪɴɢ(details)

    # ---------------------------
    # ᴘᴀʀꜱᴇ ʀᴇꜱᴜʟᴛ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ᴘᴀʀꜱᴇ_ꜱɪɢɴᴜᴘ_ʀᴇꜱᴜʟᴛ(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not resp.get("success"):
                return {
                    "success": False, 
                    "status": resp.get("error", "request_failed"),
                    "risk_score": 0,
                    "verification_sent": False,
                    "cloudways_response": resp
                }
            
            cloudways_data = resp.get("data", {})
            status_code = resp.get("status_code", 200)
            
            if status_code != 200:
                return {
                    "success": False,
                    "status": f"http_error_{status_code}",
                    "risk_score": 0,
                    "verification_sent": False,
                    "cloudways_response": cloudways_data
                }
            
            if "data" in cloudways_data and isinstance(cloudways_data["data"], dict):
                user_data = cloudways_data["data"].get("user", {})
                risk_score = user_data.get("risk_score", 0) or cloudways_data.get("risk_score", 0) or 0
                message = cloudways_data.get("message", "") or ""
                
                # ʀɪꜱᴋ ꜱᴄᴏʀᴇ ᴄʜᴇᴄᴋ - 100 ᴏʀ ᴀʙᴏᴠᴇ ɪꜱ ᴄᴏɴꜱɪᴅᴇʀᴇᴅ ʜɪɢʜ ʀɪꜱᴋ
                if risk_score >= 100:
                    return {
                        "success": False,
                        "status": "ʜɪɢʜ ʀɪꜱᴋ ꜱᴄᴏʀᴇ - ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ",
                        "risk_score": risk_score,
                        "verification_sent": False,
                        "cloudways_response": cloudways_data
                    }
                
                return {
                    "success": True,
                    "status": cloudways_data.get("message", "created"),
                    "risk_score": risk_score,
                    "verification_sent": "verify" in message.lower() or cloudways_data.get("verification_sent", False),
                    "cloudways_response": cloudways_data
                }
            
            if cloudways_data.get("success") is False:
                return {
                    "success": False, 
                    "status": cloudways_data.get("error") or cloudways_data.get("message") or "failed",
                    "risk_score": 0,
                    "verification_sent": False,
                    "cloudways_response": cloudways_data
                }
            
            return {
                "success": True, 
                "status": cloudways_data.get("message", "ok"), 
                "risk_score": cloudways_data.get("risk_score", 0),
                "verification_sent": False,
                "cloudways_response": cloudways_data
            }
            
        except Exception as e:
            return {
                "success": False, 
                "status": f"parse_error:{e}",
                "risk_score": 0,
                "verification_sent": False,
                "cloudways_response": resp
            }

    # ---------------------------
    # ɢᴇᴛ ᴄʟᴏᴜᴅᴡᴀʏꜱ ᴏʀɪɢɪɴᴀʟ ʀᴇꜱᴘᴏɴꜱᴇ ᴛᴇxᴛ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʟᴏᴜᴅᴡᴀʏꜱ_ʀᴇꜱᴘᴏɴꜱᴇ_ᴛᴇxᴛ(self, cloudways_response: Dict[str, Any]) -> str:
        """ᴇxᴛʀᴀᴄᴛ ʀᴇᴀᴅᴀʙʟᴇ ᴛᴇxᴛ ꜰʀᴏᴍ ᴄʟᴏᴜᴅᴡᴀʏꜱ ʀᴇꜱᴘᴏɴꜱᴇ"""
        try:
            if not cloudways_response:
                return "ɴᴏ ʀᴇꜱᴘᴏɴꜱᴇ ᴅᴀᴛᴀ"
            
            response_text = ""
            
            # ᴄʜᴇᴄᴋ ꜰᴏʀ ᴇʀʀᴏʀ ᴍᴇꜱꜱᴀɢᴇ
            if cloudways_response.get("error"):
                response_text += f"ᴇʀʀᴏʀ: {cloudways_response.get('error')}\n"
            
            # ᴄʜᴇᴄᴋ ꜰᴏʀ ᴍᴇꜱꜱᴀɢᴇ
            if cloudways_response.get("message"):
                response_text += f"ᴍᴇꜱꜱᴀɢᴇ: {cloudways_response.get('message')}\n"
            
            # ᴄʜᴇᴄᴋ ꜰᴏʀ ꜱᴛᴀᴛᴜꜱ
            if cloudways_response.get("status"):
                response_text += f"ꜱᴛᴀᴛᴜꜱ: {cloudways_response.get('status')}\n"
            
            # ᴄʜᴇᴄᴋ ɪɴ ᴅᴀᴛᴀ ꜱᴇᴄᴛɪᴏɴ
            data_section = cloudways_response.get("data", {})
            if data_section:
                if data_section.get("message"):
                    response_text += f"ᴅᴀᴛᴀ ᴍᴇꜱꜱᴀɢᴇ: {data_section.get('message')}\n"
                
                user_data = data_section.get("user", {})
                if user_data and isinstance(user_data, dict):
                    if user_data.get("risk_score"):
                        response_text += f"ʀɪꜱᴋ ꜱᴄᴏʀᴇ: {user_data.get('risk_score')}\n"
                    if user_data.get("status"):
                        response_text += f"ᴜꜱᴇʀ ꜱᴛᴀᴛᴜꜱ: {user_data.get('status')}\n"
            
            return response_text.strip() if response_text else "ɴᴏ ᴅᴇᴛᴀɪʟᴇᴅ ʀᴇꜱᴘᴏɴꜱᴇ ᴀᴠᴀɪʟᴀʙʟᴇ"
            
        except Exception as e:
            return f"ᴇʀʀᴏʀ ᴘᴀʀꜱɪɴɢ ʀᴇꜱᴘᴏɴꜱᴇ: {str(e)}"

    # ---------------------------
    # ᴍᴀꜱꜱ ᴄʀᴇᴀᴛᴇ ꜰᴜɴᴄᴛɪᴏɴ
    # ---------------------------
    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴍᴀꜱꜱ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "User"
        
        if not await self._ᴠɪꜱʜᴀʟ_ᴄʜᴇᴄᴋ_ᴄʜᴀɴɴᴇʟ_ᴍᴇᴍʙᴇʀꜱʜɪᴘ(user_id, context):
            await update.message.reply_text("❌ **ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀʟʟ ʀᴇQᴜɪʀᴇᴅ ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟꜱ ꜰɪʀꜱᴛ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.**")
            return
            
        self.ᴠɪꜱʜᴀʟ_ᴀᴅᴅ_ᴜꜱᴇʀ_ɪꜰ_ᴍɪꜱꜱɪɴɢ(user_id, username)

        if not context.args:
            await update.message.reply_text("📝 **ᴜꜱᴀɢᴇ:** `/mass email1.com email2.com email3.com ...`", parse_mode="Markdown")
            return

        emails = [email.strip() for email in context.args if "@" in email and "." in email.split("@")[-1]]
        
        if not emails:
            await update.message.reply_text("❌ **ɴᴏ ᴠᴀʟɪᴅ ᴇᴍᴀɪʟ ᴀᴅᴅʀᴇꜱꜱᴇꜱ ᴘʀᴏᴠɪᴅᴇᴅ.**")
            return

        available_credits = self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)
        if available_credits < len(emails):
            await update.message.reply_text(f"❌ **ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ᴄʀᴇᴅɪᴛꜱ.** ʏᴏᴜ ʜᴀᴠᴇ `{available_credits}` ᴄʀᴇᴅɪᴛꜱ ʙᴜᴛ ʀᴇQᴜᴇꜱᴛᴇᴅ `{len(emails)}` ᴀᴄᴄᴏᴜɴᴛꜱ.", parse_mode="Markdown")
            return

        if not self.ᴠɪꜱʜᴀʟ_ᴛʀʏ_ᴄᴏɴꜱᴜᴍᴇ_ᴄʀᴇᴅɪᴛ(user_id, len(emails)):
            await update.message.reply_text("💳 **ɴᴏ ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ. ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ.**")
            return

        progress_msg = await update.message.reply_text(f"🚀 **ꜱᴛᴀʀᴛɪɴɢ ᴍᴀꜱꜱ ᴄʀᴇᴀᴛɪᴏɴ ꜰᴏʀ {len(emails)} ᴀᴄᴄᴏᴜɴᴛꜱ...**")
        
        success_count = 0
        failed_count = 0
        results = []

        for i, email in enumerate(emails, 1):
            try:
                await progress_msg.edit_text(f"🔄 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ {i}/{len(emails)}: {email}**")
                
                details = self.ᴠɪꜱʜᴀʟ_ʀᴀɴᴅᴏᴍ_ᴜꜱᴇʀ_ᴅᴇᴛᴀɪʟꜱ(email)
                resp = await self.ᴠɪꜱʜᴀʟ_ꜱɪɢɴᴜᴘ_ʀᴇQᴜᴇꜱᴛ(details)
                result = self.ᴠɪꜱʜᴀʟ_ᴘᴀʀꜱᴇ_ꜱɪɢɴᴜᴘ_ʀᴇꜱᴜʟᴛ(resp)
                
                # ꜱᴀᴠᴇ ᴀᴄᴄᴏᴜɴᴛ ᴡɪᴛʜ ᴄʟᴏᴜᴅᴡᴀʏꜱ ʀᴇꜱᴘᴏɴꜱᴇ
                cloudways_response_json = json.dumps(resp.get("data", {}) if resp.get("success") else resp)
                self.ᴠɪꜱʜᴀʟ_ꜱᴀᴠᴇ_ᴀᴄᴄᴏᴜɴᴛ(user_id, details, result, cloudways_response_json)
                
                risk_score = result.get("risk_score", 0)

                if result.get("success") and risk_score < 100 and risk_score > 0:
                    success_count += 1
                    results.append(f"✅ **ꜱᴜᴄᴄᴇꜱꜱ:** {email} | ʀɪꜱᴋ: {risk_score}")
                else:
                    failed_count += 1
                    cloudways_text = self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʟᴏᴜᴅᴡᴀʏꜱ_ʀᴇꜱᴘᴏɴꜱᴇ_ᴛᴇxᴛ(result.get("cloudways_response", {}))
                    if risk_score >= 100:
                        results.append(f"❌ **ʜɪɢʜ ʀɪꜱᴋ:** {email} | ʀɪꜱᴋ: {risk_score} | {cloudways_text}")
                    else:
                        results.append(f"❌ **ꜰᴀɪʟᴇᴅ:** {email} | {cloudways_text}")

                await asyncio.sleep(2)  # ʀᴀᴛᴇ ʟɪᴍɪᴛɪɴɢ

            except Exception as e:
                failed_count += 1
                results.append(f"❌ **ᴇʀʀᴏʀ:** {email} | {str(e)}")
                continue

        # ꜱᴇɴᴅ ꜰɪɴᴀʟ ʀᴇᴘᴏʀᴛ
        report = (
            "═══════════════════════════════\n"
            "        🎯 **ᴍᴀꜱꜱ ᴄʀᴇᴀᴛɪᴏɴ ʀᴇᴘᴏʀᴛ** 🎯\n"
            "═══════════════════════════════\n\n"
            f"📧 **ᴛᴏᴛᴀʟ ᴇᴍᴀɪʟꜱ:** `{len(emails)}`\n"
            f"✅ **ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ:** `{success_count}`\n"
            f"❌ **ꜰᴀɪʟᴇᴅ:** `{failed_count}`\n"
            f"💎 **ʀᴇᴍᴀɪɴɪɴɢ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`\n\n"
            "───────────────────────────────\n"
            "📋 **ᴅᴇᴛᴀɪʟᴇᴅ ʀᴇꜱᴜʟᴛꜱ:**\n"
        )
        
        # ꜱᴘʟɪᴛ ʀᴇꜱᴜʟᴛꜱ ɪꜰ ᴛᴏᴏ ʟᴏɴɢ ꜰᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴇꜱꜱᴀɢᴇ
        results_text = "\n".join(results)
        if len(report + results_text) > 4000:
            results_text = "\n".join(results[:15]) + f"\n\n... ᴀɴᴅ {len(results) - 15} ᴍᴏʀᴇ ʀᴇꜱᴜʟᴛꜱ"
        
        final_message = report + results_text + "\n\n═══════════════════════════════"
        
        await progress_msg.delete()
        await update.message.reply_text(final_message, parse_mode="Markdown")

        # ꜱᴇɴᴅ ᴀᴅᴍɪɴ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ
        if success_count > 0:
            admin_message = (
                "📬 **ᴍᴀꜱꜱ ᴄʀᴇᴀᴛɪᴏɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ** 📬\n\n"
                f"👤 **ᴜꜱᴇʀ:** {username} ({user_id})\n"
                f"📧 **ᴛᴏᴛᴀʟ:** {len(emails)} ᴇᴍᴀɪʟꜱ\n"
                f"✅ **ꜱᴜᴄᴄᴇꜱꜱ:** {success_count}\n"
                f"❌ **ꜰᴀɪʟᴇᴅ:** {failed_count}\n"
                f"💎 **ᴄʀᴇᴅɪᴛꜱ ᴜꜱᴇᴅ:** {len(emails)}"
            )
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(admin_id, admin_message, parse_mode="Markdown")
                except Exception:
                    pass

    # ---------------------------
    # ᴛᴇʟᴇɢʀᴀᴍ ᴄᴏᴍᴍᴀɴᴅ ʜᴀɴᴅʟᴇʀꜱ
    # ---------------------------
    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ꜱᴛᴀʀᴛ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "User"
        self.ᴠɪꜱʜᴀʟ_ᴀᴅᴅ_ᴜꜱᴇʀ_ɪꜰ_ᴍɪꜱꜱɪɴɢ(user_id, username)
        
        if not await self._ᴠɪꜱʜᴀʟ_ᴄʜᴇᴄᴋ_ᴄʜᴀɴɴᴇʟ_ᴍᴇᴍʙᴇʀꜱʜɪᴘ(user_id, context):
            keyboard = [
                [InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ 1", url=f"https://t.me/{REQUIRED_CHANNELS[0][1:]}")],
                [InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ 2", url=f"https://t.me/{REQUIRED_CHANNELS[1][1:]}")],
                [InlineKeyboardButton("✅ ɪ'ᴠᴇ ᴊᴏɪɴᴇᴅ", callback_data="check_join")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "══════════════════════════\n"
                "✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄʟᴏᴜᴅᴡᴀʏꜱ ʙᴏᴛ!** ✨\n"
                "══════════════════════════\n\n"
                f"👤 **ᴜꜱᴇʀ:** @{username}\n"
                f"🆔 **ɪᴅ:** `{user_id}`\n"
                f"💎 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`\n\n"
                "🔒 **ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ, ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟꜱ ꜰɪʀꜱᴛ.**\n"
                "────────────────────────\n"
                "»»— ꯭νιѕнαL𝅃 ₊꯭♡゙꯭. » ★ / ★ ⭕ғͥғɪᴄͣɪͫ͢͢͢ᴀℓ 🇷 AJ\n"
                "────────────────────────",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            "👋 **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄʟᴏᴜᴅᴡᴀʏꜱ ʙᴏᴛ!** 👋\n\n"
            f"👤 **ᴜꜱᴇʀ:** @{username}\n"
            f"🆔 **ɪᴅ:** `{user_id}`\n"
            f"💎 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`\n\n"
            "🔧 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅꜱ:**\n"
            "├──────────────────────\n"
            "│ 💼 `/create email@example.com` \n"
            "│ 🚀 `/mass email1.com email2.com ...`\n"
            "│ 💰 `/credits` → ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴄʀᴇᴅɪᴛꜱ\n"
            "│ 📊 `/stats` → ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ (ᴀᴅᴍɪɴ)\n"
            "└──────────────────────\n\n"
            "───────────────────────\n"
            "»»— ꯭νιѕнαL𝅃 ₊꯭♡゙꯭. » ★ / ★ ⭕ғͥғɪᴄͣɪͫ͢͢͢ᴀℓ 🇷 AJ\n"
            "───────────────────────",
            parse_mode="Markdown"
        )

    async def ᴠɪꜱʜᴀʟ_ʜᴀɴᴅʟᴇ_ᴄᴀʟʟʙᴀᴄᴋ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "check_join":
            user_id = query.from_user.id
            if await self._ᴠɪꜱʜᴀʟ_ᴄʜᴇᴄᴋ_ᴄʜᴀɴɴᴇʟ_ᴍᴇᴍʙᴇʀꜱʜɪᴘ(user_id, context):
                await query.edit_message_text(
                    "✅ **ʏᴏᴜ ʜᴀᴠᴇ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ!**\n\n"
                    f"💎 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`\n\n"
                    "📧 **ꜱᴛᴀʀᴛ ᴄʀᴇᴀᴛɪɴɢ:** `/create email@example.com`\n"
                    "🚀 **ᴍᴀꜱꜱ ᴄʀᴇᴀᴛᴇ:** `/mass email1.com email2.com ...`\n"
                    "🔍 **ᴄʜᴇᴄᴋ ᴄʀᴇᴅɪᴛꜱ:** `/credits`",
                    parse_mode="Markdown"
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ 1", url=f"https://t.me/{REQUIRED_CHANNELS[0][1:]}")],
                    [InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ 2", url=f"https://t.me/{REQUIRED_CHANNELS[1][1:]}")],
                    [InlineKeyboardButton("✅ ɪ'ᴠᴇ ᴊᴏɪɴᴇᴅ", callback_data="check_join")]
                ]
                await query.edit_message_text(
                    "❌ **ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ʀᴇQᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟꜱ ʏᴇᴛ!**\n\n"
                    "ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀʟʟ ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟꜱ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴄʀᴇᴅɪᴛꜱ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await update.message.reply_text(f"💎 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`", parse_mode="Markdown")

    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴄʀᴇᴀᴛᴇ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "User"
        
        if not await self._ᴠɪꜱʜᴀʟ_ᴄʜᴇᴄᴋ_ᴄʜᴀɴɴᴇʟ_ᴍᴇᴍʙᴇʀꜱʜɪᴘ(user_id, context):
            await update.message.reply_text("❌ **ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀʟʟ ʀᴇQᴜɪʀᴇᴅ ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟꜱ ꜰɪʀꜱᴛ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.**")
            return
            
        self.ᴠɪꜱʜᴀʟ_ᴀᴅᴅ_ᴜꜱᴇʀ_ɪꜰ_ᴍɪꜱꜱɪɴɢ(user_id, username)

        if not context.args:
            await update.message.reply_text("📝 **ᴜꜱᴀɢᴇ:** `/create email@example.com`", parse_mode="Markdown")
            return

        email = context.args[0].strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            await update.message.reply_text("❌ **ɪɴᴠᴀʟɪᴅ ᴇᴍᴀɪʟ ꜰᴏʀᴍᴀᴛ.**")
            return

        if not self.ᴠɪꜱʜᴀʟ_ᴛʀʏ_ᴄᴏɴꜱᴜᴍᴇ_ᴄʀᴇᴅɪᴛ(user_id):
            await update.message.reply_text("💳 **ɴᴏ ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ. ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ. @Its_me_Vishall**")
            return

        details = self.ᴠɪꜱʜᴀʟ_ʀᴀɴᴅᴏᴍ_ᴜꜱᴇʀ_ᴅᴇᴛᴀɪʟꜱ(email)

        progress_msg = await update.message.reply_text("🔄 **ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ ᴘʀᴏxʏ sᴇʀᴠᴇʀ..........**")
        await asyncio.sleep(1)
        await progress_msg.edit_text("ᴘʀɪᴠᴀᴛᴇ ᴘʀᴏxʏ sᴇʀᴠᴇʀ ᴄᴏɴɴᴇᴄᴛ sᴜᴄᴄᴇssғᴜʟ ✅")
        await asyncio.sleep(2)
        await progress_msg.edit_text("🚀 **ᴄʟᴏᴜᴅᴡᴀʏs ᴘʀᴏᴛᴇᴄᴛɪᴏɴ ʙʏᴘᴀssɪɴɢ..........**")
        await asyncio.sleep(1)

        try:
            await progress_msg.edit_text("🔐 **ꜱᴇɴᴅɪɴɢ ʀᴇQᴜᴇꜱᴛ ᴛᴏ ᴄʟᴏᴜᴅᴡᴀʏꜱ...**")
            resp = await self.ᴠɪꜱʜᴀʟ_ꜱɪɢɴᴜᴘ_ʀᴇQᴜᴇꜱᴛ(details)
            result = self.ᴠɪꜱʜᴀʟ_ᴘᴀʀꜱᴇ_ꜱɪɢɴᴜᴘ_ʀᴇꜱᴜʟᴛ(resp)
            
            # ꜱᴀᴠᴇ ᴀᴄᴄᴏᴜɴᴛ ᴡɪᴛʜ ᴄʟᴏᴜᴅᴡᴀʏꜱ ʀᴇꜱᴘᴏɴꜱᴇ
            cloudways_response_json = json.dumps(resp.get("data", {}) if resp.get("success") else resp)
            self.ᴠɪꜱʜᴀʟ_ꜱᴀᴠᴇ_ᴀᴄᴄᴏᴜɴᴛ(user_id, details, result, cloudways_response_json)
            
            risk_score = result.get("risk_score", 0)
            cloudways_response_text = self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʟᴏᴜᴅᴡᴀʏꜱ_ʀᴇꜱᴘᴏɴꜱᴇ_ᴛᴇxᴛ(result.get("cloudways_response", {}))

            # ᴄʜᴇᴄᴋ ɪꜰ ʀɪꜱᴋ ꜱᴄᴏʀᴇ ɪꜱ 100 ᴏʀ ᴀʙᴏᴠᴇ
            if risk_score >= 100:
                txt = (
                    "❌ **ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ!** ❌\n\n"
                    f"📧 **ᴇᴍᴀɪʟ:** `{details['email']}`\n"
                    f"⚠️ **ʀᴇᴀꜱᴏɴ:** `ʜɪɢʜ ʀɪꜱᴋ ꜱᴄᴏʀᴇ - ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ`\n"
                    f"🎯 **ʀɪꜱᴋ ꜱᴄᴏʀᴇ:** `{risk_score}`\n\n"
                    f"📋 **ᴄʟᴏᴜᴅᴡᴀʏꜱ ʀᴇꜱᴘᴏɴꜱᴇ:**\n`{cloudways_response_text}`\n\n"
                    f"💎 **ʀᴇᴍᴀɪɴɪɴɢ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`"
                )
                await progress_msg.delete()
                await update.message.reply_text(txt, parse_mode="Markdown")
                # ʀᴇꜰᴜɴᴅ ᴄʀᴇᴅɪᴛ ꜰᴏʀ ʜɪɢʜ ʀɪꜱᴋ ꜰᴀɪʟᴜʀᴇ
                self.ᴠɪꜱʜᴀʟ_ʀᴇꜰᴜɴᴅ_ᴄʀᴇᴅɪᴛ(user_id)
                return

            if risk_score == 0 or not result.get("success"):
                txt = (
                    "❌ **ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ!** ❌\n\n"
                    f"📧 **ᴇᴍᴀɪʟ:** `{details['email']}`\n\n"
                    f"📋 **ᴄʟᴏᴜᴅᴡᴀʏꜱ ʀᴇꜱᴘᴏɴꜱᴇ:**\n`{cloudways_response_text}`\n\n"
                    f"💎 **ʀᴇᴍᴀɪɴɪɴɢ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`"
                )
                await progress_msg.delete()
                await update.message.reply_text(txt, parse_mode="Markdown")
                # ʀᴇꜰᴜɴᴅ ᴄʀᴇᴅɪᴛ ꜰᴏʀ ꜰᴀɪʟᴜʀᴇ
                self.ᴠɪꜱʜᴀʟ_ʀᴇꜰᴜɴᴅ_ᴄʀᴇᴅɪᴛ(user_id)
            else:
                txt = (
                    "═══════════════════════════════\n"
                    "     ✨ **ᴄʟᴏᴜᴅᴡᴀʏꜱ ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛᴇᴅ!** ✨\n"
                    "═══════════════════════════════\n\n"
                    f"👤 **ɴᴀᴍᴇ:** `{details['first_name']} {details['last_name']}`\n"
                    f"📧 **ᴇᴍᴀɪʟ:** `{details['email']}`\n"
                    f"🔑 **ᴘᴀꜱꜱᴡᴏʀᴅ:** `{details['password']}`\n"
                    f"📊 **ꜱᴛᴀᴛᴜꜱ:** `{result.get('status')}`\n"
                    f"⚠️ **ʀɪꜱᴋ ꜱᴄᴏʀᴇ:** `{risk_score}`\n"
                    f"📩 **ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴇɴᴛ:** `{result.get('verification_sent')}`\n"
                    "───────────────────────────────\n"
                    f"💎 **ʀᴇᴍᴀɪɴɪɴɢ ᴄʀᴇᴅɪᴛꜱ:** `{self.ᴠɪꜱʜᴀʟ_ɢᴇᴛ_ᴄʀᴇᴅɪᴛꜱ(user_id)}`\n"
                    "───────────────────────────────\n"
                    "✅ **ꜱᴜᴄᴄᴇꜱꜱ:** ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ! 🎉\n"
                    "═══════════════════════════════\n"
                    "     🔒  »»—⎯⁠⁠⁠⁠‌꯭꯭νιѕнαL𝅃 ₊꯭♡゙꯭. » ** 🔒\n"
                    "═══════════════════════════════"
                )

                await progress_msg.delete()
                await update.message.reply_text(txt, parse_mode="Markdown")

                owner_message = (
                    "📬 **ɴᴇᴡ ᴀᴄᴄᴏᴜɴᴛ ᴄʀᴇᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ** 📬\n\n"
                    f"👤 **ᴜꜱᴇʀ:** {username} ({user_id})\n"
                    f"📧 **ᴇᴍᴀɪʟ:** `{details['email']}`\n"
                    f"🔑 **ᴘᴀꜱꜱᴡᴏʀᴅ:** `{details['password']}`\n"
                    f"📊 **ꜱᴛᴀᴛᴜꜱ:** `{result.get('status')}`\n"
                    f"⚠️ **ʀɪꜱᴋ ꜱᴄᴏʀᴇ:** `{risk_score}`"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(admin_id, owner_message, parse_mode="Markdown")
                    except Exception:
                        pass

        except Exception as e:
            await progress_msg.delete()
            await update.message.reply_text(f"💥 **ᴇʀʀᴏʀ:** `{str(e)}`")
            # ʀᴇꜰᴜɴᴅ ᴄʀᴇᴅɪᴛ ꜰᴏʀ ᴇxᴄᴇᴘᴛɪᴏɴ
            self.ᴠɪꜱʜᴀʟ_ʀᴇꜰᴜɴᴅ_ᴄʀᴇᴅɪᴛ(user_id)

    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ꜱᴛᴀᴛꜱ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
            return

        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cur.fetchone()["total_users"]
        cur.execute("SELECT COUNT(*) as total_accounts FROM accounts")
        total_accounts = cur.fetchone()["total_accounts"]
        cur.execute("SELECT SUM(credits) as total_credits FROM users")
        total_credits = cur.fetchone()["total_credits"] or 0
        cur.execute("SELECT SUM(used) as total_used FROM users")
        total_used = cur.fetchone()["total_used"] or 0
        conn.close()

        await update.message.reply_text(
            f"📊 **ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ** 📊\n\n"
            f"👥 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:** `{total_users}`\n"
            f"📧 **ᴛᴏᴛᴀʟ ᴀᴄᴄᴏᴜɴᴛꜱ:** `{total_accounts}`\n"
            f"💎 **ᴛᴏᴛᴀʟ ᴄʀᴇᴅɪᴛꜱ:** `{total_credits}`\n"
            f"🔄 **ᴛᴏᴛᴀʟ ᴜꜱᴇᴅ:** `{total_used}`\n"
            f"📈 **ʀᴇᴍᴀɪɴɪɴɢ:** `{total_credits - total_used}`",
            parse_mode="Markdown"
        )

    async def ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴀᴅᴅᴄʀᴇᴅɪᴛꜱ(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("📝 Usage: /addcredits <user_id> <amount>")
            return

        try:
            target_user = int(context.args[0])
            amount = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid user_id or amount.")
            return

        conn = self._ᴠɪꜱʜᴀʟ_ᴄᴏɴɴᴇᴄᴛ()
        cur = conn.cursor()
        cur.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, target_user))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added `{amount}` credits to user `{target_user}`.", parse_mode="Markdown")

    # ---------------------------
    # ʀᴜɴ ʙᴏᴛ
    # ---------------------------
    def ᴠɪꜱʜᴀʟ_ʀᴜɴ(self):
        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ꜱᴛᴀʀᴛ))
        app.add_handler(CommandHandler("credits", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴄʀᴇᴅɪᴛꜱ))
        app.add_handler(CommandHandler("create", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴄʀᴇᴀᴛᴇ))
        app.add_handler(CommandHandler("mass", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴍᴀꜱꜱ))
        app.add_handler(CommandHandler("stats", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ꜱᴛᴀᴛꜱ))
        app.add_handler(CommandHandler("addcredits", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ᴀᴅᴅᴄʀᴇᴅɪᴛꜱ))
        app.add_handler(CommandHandler("broadcast", self.ᴠɪꜱʜᴀʟ_ᴄᴍᴅ_ʙʀᴏᴀᴅᴄᴀꜱᴛ))
        app.add_handler(CallbackQueryHandler(self.ᴠɪꜱʜᴀʟ_ʜᴀɴᴅʟᴇ_ᴄᴀʟʟʙᴀᴄᴋ))

        logger.info("🤖 ᴄʟᴏᴜᴅᴡᴀʏꜱ ʙᴏᴛ ɪꜱ ꜱᴛᴀʀᴛɪɴɢ...")
        app.run_polling()

# ---------------------------
# ᴇɴᴛʀʏ ᴘᴏɪɴᴛ
# ---------------------------
if __name__ == "__main__":
    bot = ᴄʟᴏᴜᴅᴡᴀʏꜱʙᴏᴛ()
    bot.ᴠɪꜱʜᴀʟ_ʀᴜɴ()