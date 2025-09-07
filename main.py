import asyncio
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
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
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
from pydantic import BaseModel
from dataclasses import dataclass
import os
load_dotenv()
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


# === OPENAI CONFIG ===
api_key = os.getenv("gemini")
MODEL = "gemini-2.0-flash"

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key,
)

set_default_openai_api("chat_completions")
set_default_openai_client(client=client)
set_tracing_disabled(True)

# === TWILIO CONFIG ===
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

# === TARGET NUMBERS ===
TARGET_NUMBERS = ["whatsapp:+923486478220", "whatsapp:+923262268830"]

# === TIMEZONE ===
karachi_tz = pytz.timezone("Asia/Karachi")

# === TWILIO CLIENT ===
client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# === Flask app ===
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

@function_tool
async def samlan_email():
    # === GOOGLE SHEETS SETUP ===
    SERVICE_ACCOUNT_FILE = "service_account.json"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    SPREADSHEET_ID = "1tFLHVczplte50zhDTfRIR8Qh-cL8vfqZmrEleb3Vx20"
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # === EMAIL SETUP ===
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "ghulamakbarabbbro110@gmail.com"
    SENDER_PASSWORD = "xjuz vvgk rvgl ngmk"

    # === ATTACHMENT ===
    RESUME_URL = "https://drive.google.com/uc?export=download&id=18fu7eID8mmZNDaL_6W3zWuJ438OLeP05"
    RESUME_PATH = "resume.pdf"


    if not os.path.exists(RESUME_PATH):
        r = requests.get(RESUME_URL)
        with open(RESUME_PATH, "wb") as f:
            f.write(r.content)

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)

    # === READ DATA FROM SHEET ===
    emails = sheet.col_values(1)[1:]           # Column A
    statuses = sheet.col_values(2)[1:]         # Column B - Status-Salman
    subjects = sheet.col_values(5)[1:]         # Column E - Subject-Salman
    bodies = sheet.col_values(6)[1:]           # Column F - Body-Salman

    sent_count = 0
    failed_count = 0
    recipients = []

    for idx, email in enumerate(emails, start=2):
        if sent_count >= 70:
            print("🚨 Daily limit (70 emails) reached. Stopping...")
            break

        status = statuses[idx-2] if idx-2 < len(statuses) else ""
        if status.strip().lower() in ["sent", "error"]:
            continue

        subject = subjects[idx-2] if idx-2 < len(subjects) else "No Subject"
        body = bodies[idx-2] if idx-2 < len(bodies) else "No Body"

        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with open(RESUME_PATH, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(RESUME_PATH)}")
            msg.attach(part)

            server.sendmail(SENDER_EMAIL, email, msg.as_string())

            sheet.update_cell(idx, 2, "Sent")  # Column B - Status-Salman
            recipients.append(email)
            sent_count += 1
            print(f"✅ Sent to {email}")

        except Exception as e:
            sheet.update_cell(idx, 2, "Error")  # Column B
            failed_count += 1
            print(f"❌ Failed to {email} - {e}")

    server.quit()

    print("\n📊 Sending Report:")
    print(f"👤 Sent by: {SENDER_EMAIL}")
    print(f"📨 Total Sent: {sent_count}")
    print(f"⚠️ Failed: {failed_count}")
    print("📧 Recipients:")
    for r in recipients:
        print(f" - {r}")


@function_tool
async def gulsher_emails():
    # === GOOGLE SHEETS SETUP ===
    SERVICE_ACCOUNT_FILE = "service_account.json"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    SPREADSHEET_ID = "1tFLHVczplte50zhDTfRIR8Qh-cL8vfqZmrEleb3Vx20"
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # === EMAIL SETUP ===
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "ghulamakbarabbbro110@gmail.com"
    SENDER_PASSWORD = "xjuz vvgk rvgl ngmk"

    # === ATTACHMENT ===
    RESUME_URL = "https://drive.google.com/uc?export=download&id=1kSsxFOwj5VNSWfLkrz-CGlplylyV7Kq5"
    RESUME_PATH = "resume.pdf"

    if not os.path.exists(RESUME_PATH):
        r = requests.get(RESUME_URL)
        with open(RESUME_PATH, "wb") as f:
            f.write(r.content)

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)

    # === READ DATA FROM SHEET ===
    emails = sheet.col_values(1)[1:]           # Column A
    statuses = sheet.col_values(3)[1:]         # Column C - Status-Gulsher
    subjects = sheet.col_values(7)[1:]         # Column G - Subject-Gulsher
    bodies = sheet.col_values(8)[1:]           # Column H - Body-Gulsher

    sent_count = 0
    failed_count = 0
    recipients = []

    for idx, email in enumerate(emails, start=2):
        if sent_count >= 70:
            print("🚨 Daily limit (70 emails) reached. Stopping...")
            break

        status = statuses[idx-2] if idx-2 < len(statuses) else ""
        if status.strip().lower() in ["sent", "error"]:
            continue

        subject = subjects[idx-2] if idx-2 < len(subjects) else "No Subject"
        body = bodies[idx-2] if idx-2 < len(bodies) else "No Body"

        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with open(RESUME_PATH, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(RESUME_PATH)}")
            msg.attach(part)

            server.sendmail(SENDER_EMAIL, email, msg.as_string())

            sheet.update_cell(idx, 3, "Sent")  # Column C - Status-Gulsher
            recipients.append(email)
            sent_count += 1
            print(f"✅ Sent to {email}")

        except Exception as e:
            sheet.update_cell(idx, 3, "Error")  # Column C
            failed_count += 1
            print(f"❌ Failed to {email} - {e}")

    server.quit()

    print("\n📊 Sending Report:")
    print(f"👤 Sent by: {SENDER_EMAIL}")
    print(f"📨 Total Sent: {sent_count}")
    print(f"⚠️ Failed: {failed_count}")
    print("📧 Recipients:")
    for r in recipients:
        print(f" - {r}")


@function_tool
async def send_custom_email_dynamic(sender_email,sender_password,recipient_email):
    """Tool to send email on-demand via WhatsApp conversation with dynamic parameters"""

    print("called email tool custom")
    # Ask for subject
    subject = "testing"
    
    # Ask for body
    body = "tested"

    # Build email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Connect to SMTP and send email
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

⚡ Guidelines:  
- When explaining your capabilities, give **detailed and clear answers**, not just short summaries.  
- Use lists and examples where helpful.  
- If the user asks for “capabilities” or “what can you do”, provide a **comprehensive answer**.  
- When using tools, clearly explain what the tool is doing.  
- Keep tone polite and professional, but **don’t limit yourself to short replies**.  
""",model=MODEL,
            tools=[samlan_email, gulsher_emails,UseremailsCridentials,send_custom_email_dynamic],
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
        runner = await Runner.run(agent, input=message, session=session,context=context)
        return runner.final_output

    print(f"📩 New message from {from_number}: {incoming_msg}")

    reply = asyncio.run(message_reply(incoming_msg))

    print("🤖 Agent Reply:", reply)

    resp = MessagingResponse()
    resp.message(reply if reply else "⚠️ Sorry, I couldn’t generate a reply.")
    return str(resp)


schedule_namaz_jobs()
app.run(host="0.0.0.0", port=5000, debug=True)





