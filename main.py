import os
import requests
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = FastAPI()

# Cloud Environment se Keys uthayega
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

def analyze_prescription(image_bytes: bytes) -> str:
    prompt = """
    आप एक अनुभवी फार्मासिस्ट और मेडिकल असिस्टेंट हैं। 
    यह डॉक्टर द्वारा लिखा गया पर्चा (Prescription) है।
    
    कृपया इसे ध्यान से पढ़ें और स्थानीय मरीज के समझने योग्य बहुत ही सरल और स्पष्ट हिंदी में जवाब दें:
    
    1. मरीज के लिए दवा की समय-सारिणी (Schedule):
       - दवा का नाम
       - कब लेनी है (सुबह / दोपहर / रात)
       - कैसे लेनी है (खाली पेट / खाने के बाद / पानी के साथ)
       - जरूरी सावधानी (यदि कोई हो)
    
    2. अंत में विनम्र सलाह दें कि डॉक्टर के कहे अनुसार ही दवा लें।
    
    जवाब का फॉर्मेट साफ-सुथरा, बुलेट पॉइंट्स और इमोजी के साथ रखें ताकि कोई भी आसानी से समझ सके।
    """

    response = ai_client.models.generate_content(
       model='gemini-2.5-flash-latest',
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
            prompt
        ]
    )
    return response.text

@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default="")
):
    twiml_resp = MessagingResponse()
    msg = twiml_resp.message()

    # Agar image aayi hai
    if NumMedia > 0 and "image" in MediaContentType0:
        try:
            auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None
            img_res = requests.get(MediaUrl0, auth=auth)
            
            if img_res.status_code == 200:
                hindi_schedule = analyze_prescription(img_res.content)
                reply_text = (
                    "🏥 *[आपकी मेडिकल शॉप, पोकरण]*\n"
                    "-----------------------------------\n"
                    f"{hindi_schedule}\n"
                    "-----------------------------------\n"
                    "📦 *दवाइयां तुरंत पैक करवाकर तैयार रखवाने के लिए अभी 'ORDER' लिखकर भेजें।*"
                )
                msg.body(reply_text)
            else:
                msg.body("पर्चा डाउनलोड नहीं हो पाया। कृपया दोबारा साफ फोटो भेजें।")
        except Exception as e:
            print(f"Error: {e}")
            msg.body("क्षमा करें, पर्चा पढ़ने में समस्या हुई। कृपया काउंटर पर दिखाएं या साफ फोटो भेजें।")
            
    elif Body.strip().upper() == "ORDER":
        msg.body("धन्यवाद! आपका ऑर्डर नोट कर लिया गया है। हम दवाइयां तैयार रख रहे हैं, आप काउंटर से प्राप्त कर सकते हैं।")
    else:
        welcome_msg = (
            "नमस्ते सा! 🙏\n"
            "कृपया अपने *डॉक्टर के पर्चे की साफ फोटो* यहां भेजें।\n"
            "हम आपको तुरंत हिंदी में समझाएंगे कि कौन सी दवा कब और कैसे लेनी है।"
        )
        msg.body(welcome_msg)

    return Response(content=str(twiml_resp), media_type="application/xml")

@app.get("/")
def home():
    return {"status": "Bot is running online 24/7"}
