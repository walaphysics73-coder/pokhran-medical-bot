import os
import time
import requests
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = FastAPI()

# Environment variables se keys uthayega
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

ai_client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_prescription(image_bytes: bytes) -> str:
    prompt = """
आप एक बहुत ही अनुभवी भारतीय फार्मासिस्ट और मेडिकल असिस्टेंट हैं।
यह एक भारतीय डॉक्टर द्वारा लिखा गया पर्चा (Prescription) या दवा की पर्ची/स्ट्रिप है।

डॉक्टरों की लिखावट अक्सर घसीट (cursive/messy handwriting) होती है। आप अपने अनुभव और भारतीय दवाओं के नामों (जैसे Cefpodoxime, Ofloxacin, Paracetamol, Becosules, Pan-D आदि) के आधार पर इसे ध्यान से पढ़ें।

मरीज के समझने योग्य बहुत ही सरल, स्पष्ट और शुद्ध हिंदी में जवाब दें:

1. 📋 **मरीज की दवा समय-सारिणी (Schedule):**
   - दवा का नाम
   - खुराक (कितनी गोली/चम्मच)
   - समय (सुबह / दोपहर / रात)
   - निर्देश (खाना खाने से पहले या बाद में)

2. ⚠️ **ज़रूरी सावधानियां:**
   - कोई खास परहेज या सावधानी।

3. 🛑 **नोट:** यह AI द्वारा निकाली गई जानकारी है। कृपया दवा लेने से पहले नजदीकी फार्मासिस्ट या डॉक्टर से पुष्टि अवश्य करें।

जवाब साफ-सुथरा, बुलेट पॉइंट्स और उपयुक्त इमोजी के साथ रखें ताकि कोई भी मरीज आसानी से समझ सके।
"""

    # High demand ya temporary error aane par 3 baar retry karega
    last_exception = None
    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_exception = e
            time.sleep(2)  # 2 second wait karke dubara koshish karega

    if last_exception:
        raise last_exception

    return "क्षमा करें, पर्चा पढ़ने में समस्या हुई। कृपया काउंटर पर दिखाएं या साफ फोटो भेजें।"


@app.get("/")
def home():
    return {"status": "Medical Bot is Active and Running!"}


@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default=""),
):
    resp = MessagingResponse()
    msg = resp.message()

    # Agar user ne photo bheji hai
    if NumMedia > 0 and MediaUrl0:
        try:
            # Twilio media ko basic auth ke saath download karna zaroori hai
            auth = None
            if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

            media_res = requests.get(MediaUrl0, auth=auth, timeout=20)

            if media_res.status_code == 200:
                analysis = analyze_prescription(media_res.content)
                msg.body(analysis)
            else:
                msg.body(
                    "फोटो डाउनलोड करने में समस्या आई। कृपया दोबारा साफ फोटो भेजें।"
                )
        except Exception as err:
            print(f"Error analyzing image: {err}")
            msg.body(
                "क्षमा करें, पर्चा पढ़ने में समस्या हुई। कृपया काउंटर पर दिखाएं या साफ फोटो भेजें।"
            )
    else:
        # Agar user ne text (Hi/Hello) bheja hai
        greeting = (
            "नमस्ते सा! 🙏\n\n"
            "कृपया अपने डॉक्टर के पर्चे या दवा की साफ फोटो यहां भेजें।\n"
            "हम आपको तुरंत हिंदी में समझाएंगे कि कौन सी दवा कब और कैसे लेनी है।"
        )
        msg.body(greeting)

    return Response(content=str(resp), media_type="application/xml")
