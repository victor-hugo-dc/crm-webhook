from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("BASE_URL"), "https://framer.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WebhookData(BaseModel):
    Name: str
    Email: str
    PhoneNumber: Optional[str] = None # Example if Phone Number was optional

def construct_response(name: str, email: str, phone: Optional[str]) -> dict:
    response: str = f"🆕 **New Lead**\n**Name:** {name}\n**Email:** {email}\n"
    if phone: response = f"{response}**Phone:** {phone}"
    return { "content": response }

def extract_name(data: WebhookData):
    return data.Name.strip().split(" ")[:2]

@app.post("/webhook")
async def webhook_endpoint(data: WebhookData): # Use the Pydantic model for request body
    try:
        first_name, last_name = extract_name(data)
        email = data.Email
        phone = data.PhoneNumber

        FRAPPE_CRM_URL = os.getenv("FRAPPE_CRM_URL")
        DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
        API_KEY    = os.getenv("FRAPPE_API_KEY")
        API_SECRET = os.getenv("FRAPPE_API_SECRET")

        if all([FRAPPE_CRM_URL, API_KEY, API_SECRET]):
            headers = {
                "Authorization": f"token {API_KEY}:{API_SECRET}",
                "Content-Type": "application/json"
            }

            frappe_payload = {
                "doc": {
                    "doctype":"CRM Lead",
                    "no_of_employees":"1-10",
                    "lead_owner":"Administrator",
                    "status":"New",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                }
            }
            
            frappe_response = requests.post(
                FRAPPE_CRM_URL,
                json=frappe_payload,
                headers=headers
            )
            frappe_response.raise_for_status() # Raise an exception for HTTP errors

        if DISCORD_WEBHOOK_URL:
            name = f"{first_name} {last_name}"
            discord_payload = construct_response(name, email, phone)
            discord_response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=discord_payload,
                headers={"Content-Type": "application/json"}
            )
            discord_response.raise_for_status() # Raise an exception for HTTP errors

        return JSONResponse(content={"message": "Webhook processed successfully"}, status_code=200)

    except HTTPException as e:
        raise e

    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": f"External service error: {str(e)}"}, status_code=502)
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
