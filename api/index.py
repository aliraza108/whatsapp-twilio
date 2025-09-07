from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = FastAPI()

@app.get("/")
def home():
    return {"message": "FastAPI is running on Vercel 🚀"}

@app.post("/send-email")
async def send_email(request: Request):
    data = await request.json()
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")
    receiver_email = data.get("to")
    subject = data.get("subject", "No Subject")
    body = data.get("body", "")

    try:
        # build email
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        return JSONResponse({"status": "success", "message": f"Email sent to {receiver_email}"})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
