import asyncio
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from agents import Runner, Agent, set_default_openai_api, set_tracing_disabled, AsyncOpenAI, set_default_openai_client, function_tool, SQLiteSession, RunContextWrapper, run_context
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
from pydantic import BaseModel
from dataclasses import dataclass
from dotenv import load_dotenv

# Load env
load_dotenv()

# =====================
# USER EMAIL CREDENTIALS
# =====================
@dataclass
class Useremailinfo:  
    senderemail: str
    senderpassword: str

@function_tool
async def UseremailsCridentials(wrapper: RunContextWrapper[Useremailinfo]) -> str:  
    """Fetch the user email and password from the context"""
    return f"✅ user email is {wrapper.context.senderemail} and password is {wrapper.context.senderpassword}"

user_credentials_map = {
    "whatsapp:+923486478220": Useremailinfo(senderemail="salam@gmail.com", senderpassword="2s4s5d"),
    "whatsapp:+923262268830": Useremailinfo(senderemail="ghulamakbarabbbro110@gmail.com", senderpassword="xjuz vvgk rvgl ngmk")
}

# =====================
# OPENAI CONFIG
# =====================
api_key = os.getenv("gemini")
MODEL = "gemini-2.0-flash"

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key,
)

set_default_openai_api("chat_completions")
set_default_openai_client(client=client)
set_tracing_disabled(True)

# =====================
# TWILIO CONFIG
# =====================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

TARGET_NUMBERS = ["whatsapp:+923486478220", "whatsapp:+923262268830"]
karachi_tz = pytz.timezone("Asia/Karachi")

client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

# ======================
# 🚀 Namaz Reminder Code
# ======================
def send_whatsapp_message(body):
    """Send WhatsApp message to all target numbers"""
    for number in TARGET_NUMBERS:
        client_twilio.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=number,
            body=body
        )
        print(f"✅ Sent WhatsApp to {number}: {body}")

def schedule_namaz_jobs():
    """Schedule daily namaz reminders"""
    scheduler = BackgroundScheduler(timezone=karachi_tz)

    namaz_times = {
        "Fajr": "05:00",
        "Dhuhr": "13:30",
        "Asr": "16:30",
        "Maghrib": "18:45",
        "Isha": "20:00"
    }

    for namaz, time_str in namaz_times.items():
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            send_whatsapp_message,
            "cron",
            hour=hour,
            minute=minute,
            args=[f"🕌 It's time for {namaz} prayer in Karachi."]
        )
        print(f"📅 Scheduled {namaz} at {time_str} Karachi time")

    scheduler.start()

# =====================
# EMAIL TOOLS (same as yours)
# =====================
@function_tool
async def samlan_email():
    # your full samlan_email code here (unchanged)
    return "✅ Salman emails sent!"

@function_tool
async def gulsher_emails():
    # your full gulsher_emails code here (unchanged)
    return "✅ Gulsher emails sent!"

@function_tool
async def send_custom_email_dynamic(sender_email, sender_password, recipient_email):
    """Tool to send email on-demand via WhatsApp conversation with dynamic parameters"""

    subject = "testing"
    body = "tested"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return f"✅ Email successfully sent to {recipient_email} from {sender_email}."
    except Exception as e:
        return f"❌ Failed to send email: {e}"

# ======================
# 💬 WhatsApp Agent Bot
# ======================
sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body")
    from_number = request.form.get("From")

    async def message_reply(message: str):
        agent = Agent(
            name="Agent",
            instructions="""
You are a personalized AI Assistant for WhatsApp users. Your main goal is to **help users send emails** and provide support.
""",
            model=MODEL,
            tools=[samlan_email, gulsher_emails, UseremailsCridentials, send_custom_email_dynamic],
        )
        
        user_id = from_number
        if user_id not in sessions:
            sessions[user_id] = SQLiteSession(f"conversation_{user_id}")
            print(f"🆕 Created new session for {user_id}")
        else:
            print(f"♻️ Loaded existing session for {user_id}")

        session = sessions[user_id]
        context = user_credentials_map.get(user_id)
        if not context:
            return "Sorry, your credentials are not configured"
        runner = await Runner.run(agent, input=message, session=session, context=context)
        return runner.final_output

    print(f"📩 New message from {from_number}: {incoming_msg}")
    reply = asyncio.run(message_reply(incoming_msg))
    print("🤖 Agent Reply:", reply)

    resp = MessagingResponse()
    resp.message(reply if reply else "⚠️ Sorry, I couldn’t generate a reply.")
    return str(resp)

# ⚠️ Do not run app.run() on Vercel!
# schedule_namaz_jobs() should only run once in background if you host it on a real server (not Vercel serverless)
