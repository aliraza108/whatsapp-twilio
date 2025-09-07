from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def home():
    return {"message": "FastAPI is running on Vercel 🚀"}

@app.post("/send-email")
def send_email(data: dict):
    # put your email logic here
    return JSONResponse({"status": "Email sent", "data": data})
