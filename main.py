from balethon import Client
import requests
import asyncio
from google import genai
from fastapi import FastAPI
import uvicorn
from threading import Thread

# ۱. تنظیمات توکن بله و کلیدهای هوش مصنوعی شما
BALE_TOKEN = '859462436:Nm48AVYw291Z4K2qvU_9sO9YojIebpMAM8Y'
GEMINI_API_KEY = 'AQ.Ab8RN6IwxC3_QhWPI3XjMLRDpkfAM1Ru1gVZsslurY3xg2vT3A'
GROQ_API_KEY = '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'

# ۲. راه‌اندازی کلاینت‌ها و سرور وب برای بیدار ماندن در رندر
app = FastAPI()
bot = Client(BALE_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

@app.get("/")
def home():
    return {"status": "Multi-Agent Brain is running successfully!"}

# ۳. تابع دریافت پاسخ از Gemini گوگل
def fetch_gemini(user_text):
    try:
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=user_text,
        )
        return response.text
    except Exception as e:
        return f"[خطای Gemini: {e}]"

# ۴. تابع دریافت پاسخ از Groq (مدل Llama)
def fetch_groq(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a precise assistant. Reply in Persian."},
            {"role": "user", "content": user_text}
        ]
    }
    try:
        response = requests.post(url, json=data, timeout=15)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"[خطای Groq: {response.status_code}]"
    except Exception as e:
        return f"[خطای ارتباط با Groq: {e}]"

# ۵. سیستم داوری ارشد برای ادغام پاسخ‌ها
def judge_and_merge(user_prompt, answer_a, answer_b):
    judge_prompt = f"""
    تو داور ارشد یک سیستم چند ایجنتی هستی. 
    یک کاربر پیامی فرستاده است و دو مدل هوش مصنوعی مختلف به آن پاسخ داده‌اند.
    وظیفه تو این است که هر دو پاسخ را با دقت بررسی کنی، اطلاعات غلط یا ناقص را حذف کنی، 
    بخش‌های خوب و تکمیلی هر دو را با هم ترکیب کنی و یک پاسخ نهاییِ فوق‌العاده کامل، 
    دقیق، روان و با لحن بسیار زیبا به زبان فارسی تولید کنی. 
    مستقیماً پاسخ نهایی را خروجی بده و وارد حاشیه یا توضیح در مورد مدل‌ها نشو.

    پیام کاربر: "{user_prompt}"
    پاسخ مدل اول (Gemini): "{answer_a}"
    پاسخ مدل دوم (Groq): "{answer_b}"
    
    پاسخ نهایی و ادغام‌شده تو:
    """
    try:
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=judge_prompt,
        )
        return response.text
    except Exception as e:
        # در صورت خطای احتمالی داور، پاسخ مدل اول که سالم است را برمی‌گرداند
        return answer_a if "[خطا" not in answer_a else answer_b

# ۶. مدیریت پیام‌های بله به صورت همزمان (Parallel Async)
@bot.on_message()
async def answer_message(message):
    if not message.text:
        return
        
    try:
        loop = asyncio.get_event_loop()
        
        # ارسال همزمان درخواست‌ها به هر دو مدل برای بالا رفتن سرعت ربات
        task_gemini = loop.run_in_executor(None, fetch_gemini, message.text)
        task_groq = loop.run_in_executor(None, fetch_groq, message.text)
        
        # منتظر ماندن برای دریافت نتایج هر دو مدل
        ans_gemini, ans_groq = await asyncio.gather(task_gemini, task_groq)
        
        # سپردن نتایج به داور هوشمند برای ساخت پاسخ نهایی و عالی
        final_reply = await loop.run_in_executor(None, judge_and_merge, message.text, ans_gemini, ans_groq)
        
        # ارسال پاسخ نهایی به کاربر در پیام‌رسان بله
        await message.reply(final_reply)
        
    except Exception as e:
        print(f"Error in multi-agent system: {e}")
        try:
            await message.reply("مشکلی در فرآیند تحلیل همزمان اتاق فکر رخ داد.")
        except:
            pass

def run_bale():
    bot.run()

if __name__ == '__main__':
    # اجرای ربات بله روی Thread مجزا برای جلوگیری از بلاک شدن سرور وب
    bale_thread = Thread(target=run_bale)
    bale_thread.daemon = True
    bale_thread.start()
    
    # اجرای FastAPI روی پورتی که رندر به پروژه اختصاص می‌دهد
    uvicorn.run(app, host="0.0.0.0", port=8000)
