import streamlit as st
import pandas as pd
import numpy as np
import random
import os
import sys
import google.generativeai as genai
from google.generativeai.types import StopCandidateException
import traceback
import re
import time
from datetime import datetime, timedelta # <-- لاستخدام الوقت والتاريخ

# ---!!! إعدادات وضع الصيانة (تحديد المدة) !!!---
MAINTENANCE_MODE = True
MAINTENANCE_DURATION_HOURS = 7


maintenance_end_time = None
if MAINTENANCE_MODE:
    # حساب وقت انتهاء الصيانة بناءً على الوقت الحالي والمدة المحددة
    maintenance_end_time = datetime.now() + timedelta(hours=MAINTENANCE_DURATION_HOURS)
    print(f"INFO: Maintenance mode activated. Ends at approximately: {maintenance_end_time}")
# --- نهاية إعدادات وضع الصيانة ---


# --- التحقق من وضع الصيانة في بداية الكود ---
if MAINTENANCE_MODE and maintenance_end_time: # نتأكد أن وقت الانتهاء تم حسابه
    st.set_page_config(page_title="صيانة | Qurate", page_icon="🛠️")
    st.title("🛠️ عذرًا، كيوري تحت الصيانة الآن 🛠️")

    # ---!!! تعديل هنا: عرض رسالة المدة فقط وإزالة العداد والحلقة !!!---
    st.warning(f"نحن نجري بعض التحسينات! من المتوقع أن نعود خلال {MAINTENANCE_DURATION_HOURS} ساعات تقريبًا.")

    # (اختياري) إضافة صورة
    # st.image("your_maintenance_image_url.png", caption="نعود قريبًا...")

    # --- إضافة معلومات تشخيصية بسيطة (اختياري) ---
    st.caption(f"وضع الصيانة: مُفعّل | ينتهي تقريبًا في: {maintenance_end_time.strftime('%Y-%m-%d %H:%M:%S')} (بتوقيت الخادم)")

    # --- إيقاف تنفيذ باقي الكود ---
    st.stop()
# --- START OF FILE qurate.py ---
st.set_page_config(page_title="كيوري | Qurate", page_icon="✨")

# --- 1. Configuration ---
DB_PATH = "products_database_final_clean_v3_tags.csv"
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" # أو "gemini-1.0-pro" إذا كنت تفضل
MAX_EXAMPLE_PRODUCTS = 4 # الحد الأقصى للمنتجات المعروضة كأمثلة
HISTORY_LENGTH = 8 # عدد الرسائل السابقة لإرسالها كـ context لـ Gemini
LOGO_PATH = "qurate_logo.png" # مسار الشعار (اختياري)

# --- 2. Load Product Database ---
@st.cache_resource(show_spinner="جاري تحميل بيانات المنتجات...")
def load_product_database(db_path):
    """Loads, validates, and preprocesses the product database from a CSV file."""
    db = pd.DataFrame()
    print(f"--- Attempting to load Product Database from: {db_path} ---")
    if not os.path.exists(db_path):
        st.error(f"ملف قاعدة البيانات غير موجود في المسار المحدد: {db_path}")
        print(f"ERROR: Database file not found at {db_path}")
        return db # Return empty DataFrame

    try:
        db = pd.read_csv(db_path)
        print(f"INFO: Read {len(db)} rows initially from {db_path}")

        # --- Validation ---
        required_cols = ['id', 'name', 'price', 'product_url', 'image_url', 'store', 'category', 'tags']
        missing_cols = [col for col in required_cols if col not in db.columns]
        if missing_cols:
            # Attempt to gracefully handle missing 'id' if possible, else raise error
            if 'id' in missing_cols and 'product_url' in db.columns:
                 print("WARN: 'id' column missing, attempting to use 'product_url' as id.")
                 db['id'] = db['product_url'] # Use URL as a fallback ID
                 missing_cols.remove('id')
            if missing_cols: # If other required columns are still missing
                 raise ValueError(f"قاعدة البيانات تفتقد للأعمدة المطلوبة: {missing_cols}")

        # --- Preprocessing ---
        # Handle potential duplicates in ID (after potentially creating it from URL)
        if db['id'].duplicated().any():
            print(f"WARN: Found {db['id'].duplicated().sum()} duplicate IDs, keeping first occurrence.")
            db = db.drop_duplicates(subset=['id'], keep='first')

        # Set index (important AFTER handling duplicates)
        db['id'] = db['id'].astype(str) # Ensure ID is string
        db = db.set_index('id', drop=False) # Keep 'id' also as a column if needed elsewhere

        # Clean essential columns
        db = db.dropna(subset=['name', 'product_url', 'image_url', 'price']) # Drop rows missing these essentials
        print(f"INFO: Rows after dropping NA in essential columns: {len(db)}")

        # Ensure correct types and fill missing optional data
        db['price'] = pd.to_numeric(db['price'], errors='coerce')
        db = db.dropna(subset=['price']) # Drop rows where price couldn't be converted
        print(f"INFO: Rows after coercing price to numeric and dropping NA: {len(db)}")

        db['tags'] = db['tags'].fillna('').astype(str)
        db['category'] = db['category'].fillna('Unknown').astype(str)
        db['brand'] = db['brand'].fillna('') # Fill missing brands with empty string

        print(f"INFO: Loaded and validated {len(db)} products successfully.")
        return db

    except FileNotFoundError:
        st.error(f"خطأ: ملف قاعدة البيانات غير موجود في {db_path}")
        print(f"ERROR: FileNotFoundError for {db_path}")
        return pd.DataFrame()
    except ValueError as ve:
        st.error(f"خطأ في بيانات قاعدة البيانات: {ve}")
        print(f"ERROR: ValueError during DB processing: {ve}")
        traceback.print_exc()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"خطأ فادح غير متوقع في تحميل أو معالجة {db_path}: {e}")
        print(f"ERROR: Unexpected error loading/processing {db_path}: {e}")
        traceback.print_exc()
        return pd.DataFrame()

# Load the database immediately
products_db = load_product_database(DB_PATH)
if products_db.empty:
    st.error("فشل تحميل قاعدة بيانات المنتجات. قد لا تعمل ميزة عرض الأمثلة.")
print(f"--- Product DB loaded status: {'OK' if not products_db.empty else 'Failed'}. Rows: {len(products_db)} ---")

# --- 3. Gemini API Setup ---
GEMINI_AVAILABLE = False
model = None
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY")
    if API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME)
        GEMINI_AVAILABLE = True
        print(f"INFO: Gemini AI Model configured successfully ({GEMINI_MODEL_NAME}).")
    else:
        st.warning("لم يتم توفير مفتاح Google API في ملف الأسرار (secrets.toml).", icon="🔑")
        print("WARN: GOOGLE_API_KEY not found or empty in Streamlit secrets.")
except KeyError:
     st.warning("لم يتم العثور على إعداد 'GOOGLE_API_KEY' في ملف الأسرار (secrets.toml).", icon="🔑")
     print("WARN: 'GOOGLE_API_KEY' key missing in Streamlit secrets.")
except Exception as e:
    st.error(f"حدث خطأ أثناء إعداد نموذج الذكاء الاصطناعي Gemini: {e}", icon="❗")
    print(f"ERROR: Failed to configure Gemini: {e}")
    traceback.print_exc()
    GEMINI_AVAILABLE = False

# --- 4. Salon Data and Suggestion Function ---
@st.cache_data
def load_salon_data():
    """Loads predefined salon data."""
    # يمكنك توسيع هذه القائمة أو تحميلها من ملف إذا كبرت
    return {
        "صالون": [
            "صالون الجمال العصري",
            "سبا الأميرات",
            "صالون في اي بي للسيدات",
            "مركز العناية بالشعر والبشرة",
            "كوينز سبا"
        ]
    }
salon_data = load_salon_data()

def suggest_salons(query):
    """Suggests salons based on keywords in the query."""
    suggestions = []
    query_lower = query.lower()
    # توسيع قائمة الكلمات المفتاحية لتكون أكثر شمولاً
    salon_keywords = ["صالون", "كوافير", "شعر", "قص", "صبغة", "تجميل", "سبا", "ميكب ارتست", "مكياج", "بديكير", "مانيكير"]
    if any(keyword in query_lower for keyword in salon_keywords):
        # استخدم set لضمان عدم التكرار ثم حولها لقائمة
        suggestions.extend(salon_data.get("صالون", []))
    # إرجاع أول 3 اقتراحات فريدة
    return list(dict.fromkeys(suggestions))[:3]

# --- 5. Function to Get Random Product Examples ---
def get_random_product_examples(category_query, db, num_examples=MAX_EXAMPLE_PRODUCTS):
    """
    Selects random product examples from the database based on a category query.
    Falls back to general random examples if category is not identified or empty.
    """
    if db is None or db.empty:
        print("DEBUG (get_random): Database is empty or None, cannot provide examples.")
        return []

    print(f"DEBUG (get_random): Attempting to find examples for query: '{category_query}'")
    target_category = None
    query_lower = category_query.lower()

    # تحسين خريطة الفئات لتكون أكثر مرونة
    # المفتاح هو الكلمة المفتاحية في استعلام المستخدم (صغير)، القيمة هي اسم الفئة في قاعدة البيانات
    cat_map = {
        "abaya": "Abayas", "عباية": "Abayas", "عبايات": "Abayas",
        "dress": "Dresses", "فستان": "Dresses", "فساتين": "Dresses",
        "shoe": "Shoes", "حذاء": "Shoes", "أحذية": "Shoes", "كعب": "Shoes", "شوز": "Shoes", "جوتي": "Shoes", "نعال": "Shoes",
        "bag": "Bags", "شنطة": "Bags", "حقيبة": "Bags", "حقائب": "Bags", "شنط": "Bags"
        # يمكنك إضافة المزيد هنا (مثل: مجوهرات، اكسسوارات، قمصان، بناطيل)
    }

    # البحث عن الكلمة المفتاحية في الاستعلام
    for keyword, cat_name in cat_map.items():
        # استخدام حدود الكلمات (\b) لضمان تطابق الكلمة الكاملة (اختياري ولكن قد يكون أدق)
        if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
            target_category = cat_name
            print(f"DEBUG (get_random): Identified target category '{target_category}' based on keyword '{keyword}'.")
            break # وجدنا فئة، لا داعي للمتابعة

    examples_list = []
    if target_category and 'category' in db.columns:
        # فلترة قاعدة البيانات بناءً على الفئة المستهدفة (غير حساس لحالة الأحرف)
        # استخدام regex=False لتجنب معاملة اسم الفئة كتعبير نمطي
        category_df = db[db['category'].str.contains(target_category.replace('s',''), case=False, na=False, regex=False)] # إزالة 's' للمرونة
        if not category_df.empty:
            sample_size = min(num_examples, len(category_df))
            examples_df = category_df.sample(n=sample_size, random_state=random.randint(1, 10000)) # زيادة نطاق العشوائية
            examples_list = examples_df.to_dict('records') # تحويل DataFrame إلى قائمة قواميس
            print(f"DEBUG (get_random): Found {len(examples_list)} examples for category '{target_category}'.")
            if examples_list: print(f"  First example keys: {list(examples_list[0].keys())}") # تأكد من وجود المفاتيح المطلوبة
        else:
            print(f"DEBUG (get_random): No products found matching derived category '{target_category}'. Will try general examples.")
            target_category = None # إعادة تعيين للإشارة إلى أننا نحتاج لأمثلة عامة

    # إذا لم يتم تحديد فئة أو لم نجد منتجات في الفئة المحددة، نعرض أمثلة عشوائية عامة
    if not examples_list:
        print(f"DEBUG (get_random): Category '{target_category if target_category else 'N/A'}' not found or empty. Returning general random sample.")
        available_products = len(db)
        if available_products > 0:
            sample_size = min(num_examples, available_products)
            examples_df = db.sample(n=sample_size, random_state=random.randint(1, 10000))
            examples_list = examples_df.to_dict('records')
            print(f"DEBUG (get_random): Found {len(examples_list)} general examples.")
            if examples_list: print(f"  First general example keys: {list(examples_list[0].keys())}")
        else:
             print("DEBUG (get_random): Database is effectively empty after filtering/cleaning, cannot provide general examples.")

    return examples_list

def format_price(price_num, price_text_fallback=""):
    """Formats a numeric price into Qatari Riyal currency format."""
    if pd.isna(price_num):
        return price_text_fallback + " ر.ق" if isinstance(price_text_fallback, str) and price_text_fallback else "السعر غير متوفر"
    try:
        # Format with commas for thousands and 2 decimal places
        return f"{float(price_num):,.2f} ر.ق"
    except (ValueError, TypeError):
        # Fallback if conversion fails
        print(f"WARN (format_price): Could not format price '{price_num}', using fallback '{price_text_fallback}'.")
        return price_text_fallback + " ر.ق" if isinstance(price_text_fallback, str) and price_text_fallback else "السعر غير متوفر"

# --- 6. Helper Function to Get AI Text Response from Gemini ---
def get_ai_text_response(user_prompt, chat_history):
    """Gets a text-only response from the Gemini model based on the prompt and history."""
    print(f"DEBUG (get_ai_text): Requesting AI Text Response for prompt: '{user_prompt[:100]}...'")

    # --- بناء الموجه (Prompt) ---
    # (استخدم الـ Prompt v7 الفعلي الخاص بك هنا)
    system_prompt = """أنتِ "كيوري"، صديقتكِ المقربة وشريكتكِ في الأناقة والموضة في قطر.

**الشخصية الأساسية:** ودودة جداً، لطيفة، إيجابية، داعمة، وشغوفة بالموضة. خبيرة في تنسيق الملابس والألوان والصيحات الحديثة في قطر والخليج.

**اللغة واللهجة:**
*   **الأساس:** تحدثي باللهجة القطرية الحديثة بطلاقة (مثل المستخدم). استخدمي عبارات مثل "حبيبتي"، "فديتج"، "من عيوني"، "يا هلا"، "شلونج؟"، "شخبارج؟". حافظي على هذه اللهجة عندما يتحدث المستخدم بالعربية.
*   **دعم الإنجليزية:** إذا تحدث المستخدم بشكل أساسي باللغة الإنجليزية، قومي بالرد بلغة إنجليزية واضحة وودودة. حافظي على شخصيتك اللطيفة والخبيرة بالموضة في قطر، ولكن تواصلي بالإنجليزية. إذا عاد المستخدم للتحدث بالعربية، عودي فورًا للهجتك القطرية.

**مهمتك:**
1.  **الدردشة العامة:** كوني صديقة تستمع وتقدم الدعم والتشجيع في مواضيع الموضة والحياة اليومية (بشكل عام).
2.  **نصائح الموضة والأناقة:** قدمي نصائح عملية ومفيدة حول تنسيق الملابس، الألوان، اختيار الإكسسوارات، ملابس المناسبات المختلفة (أعراس، دوام، طلعات)، وآخر الصيحات في قطر. كوني محددة إذا أمكن.
3.  **اقتراح صالونات:** إذا سأل المستخدم عن صالونات أو خدمات تجميل، اذكري بعض الأسماء المعروفة بشكل عام في قطر (لا تقدمي تفاصيل دقيقة أو روابط أو أسعار).
4.  **التعامل مع طلب الأمثلة:** إذا طلب المستخدم رؤية أمثلة منتجات (مثل "ورني عباية"، "أبي أشوف فساتين"، "Show me examples of bags")، ردي عليه بشكل مناسب ولطيف بأنكِ ستحاولين عرض بعض الأفكار (مثلاً: "تامرين حبيبتي، بشوف لج الحين"، "من عيوني، هذي بعض الأمثلة اللي ممكن تعجبج"، "Sure! Let me show you some ideas."). **لا تخترعي تفاصيل منتجات بنفسكِ.** التطبيق سيعرض الأمثلة الفعلية بشكل منفصل.
5.  **تجنب البحث الوهمي:** لا تدّعي أنكِ تبحثين في متاجر معينة أو تقارنين أسعاراً أو تتوفر لديكِ معلومات المخزون. حافظي على دوركِ كمستشارة موضة تقدم الإلهام والنصائح العامة.

**معلومات عنكِ (مهم جداً):**
*   **إذا سُئلتِ "من صنعك؟" أو "من طورك؟" أو "من أنتِ؟" أو ما شابه (بالعربي أو الإنجليزي):** ردي بأنكِ تم تطويركِ بواسطة **"فريق كيوري التقني"** أو **"Qurate's technical team"**. **تجنبي تمامًا ذكر "Google" أو "Gemini" أو "نموذج لغوي كبير" أو أي تفاصيل عن التكنولوجيا الأساسية.** ركزي على كونكِ "كيوري". (مثال للرد: "أنا كيوري، طوّرني فريق كيوري التقني عشان أساعدج في كل شي يخص الأناقة!")

**الحدود:**
*   لا تقدمي نصائح طبية، قانونية، مالية، أو شخصية حساسة جداً.
*   إذا خرج الموضوع عن الموضة والأناقة والجمال والدردشة اللطيفة، حاولي إعادة المحادثة بلطف للموضوع الأساسي.
*   لا تقومي بعمليات شراء أو حجوزات أو تقديم معلومات اتصال مباشرة للمتاجر أو الصالونات.

**الهدف:** كوني مستشارة الموضة الرقمية الأكثر لطفاً وفائدة في قطر، سواء بالعربي أو بالإنجليزي!
"""

    final_response_text = "عفوًا حبيبتي، ما فهمت عدل ممكن توضحين أكثر؟ 🤔" # Default fallback
    if not GEMINI_AVAILABLE or model is None:
        print("WARN (get_ai_text): Gemini model is not available.")
        return "أعتذر فديتج، النموذج غير متاح حالياً. 🥺 جربي بعد شوي."

    try:
        # --- بناء سجل المحادثة لـ Gemini ---
        gemini_history = []
        # خذ آخر HISTORY_LENGTH رسائل (مع التأكد أنها بالتنسيق الصحيح)
        relevant_history = chat_history[-HISTORY_LENGTH:]
        for msg_data in relevant_history:
            role = "user" if msg_data.get("role") == "user" else "model"
            # استخلاص النص فقط من المحتوى
            content = msg_data.get("content")
            text_content = ""
            if isinstance(content, str):
                text_content = content
            elif isinstance(content, dict):
                text_content = content.get("text", "")

            if text_content: # أضف فقط إذا كان هناك نص
                gemini_history.append({"role": role, "parts": [{"text": text_content}]})
            # لا نرسل بيانات المنتجات السابقة إلى Gemini

        # --- بناء الـ Prompt الكامل ---
        # لا نحتاج إلى بناء prompt معقد هنا لأننا فقط نريد رد نصي عام
        # نرسل فقط الرسالة الأخيرة للمستخدم والسجل
        print(f"DEBUG (get_ai_text): Sending last user prompt and history (len={len(gemini_history)}) to Gemini {GEMINI_MODEL_NAME}.")

        # تهيئة المحادثة من السجل + الرسالة الجديدة
        # ملاحظة: قد تحتاج لتعديل هذه الطريقة إذا كنت تستخدم `start_chat`
        chat_session = model.start_chat(history=gemini_history)

        # إعدادات التوليد والسلامة
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=1000, # زيادة طفيفة للردود الأطول المحتملة
            temperature=0.75, # للحفاظ على بعض الإبداع
            # top_p=0.9, # يمكنك تجربتها للتحكم بالتنوع
            # top_k=40   # يمكنك تجربتها للتحكم بالتنوع
        )
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        # إرسال رسالة المستخدم الحالية والحصول على الرد
        # نضيف الـ System Prompt كأول رسالة في السجل إذا لم يكن النموذج يدعمه مباشرة
        # بالنسبة لـ Flash، قد يكون من الأفضل وضعه كجزء من أول رسالة للمستخدم أو ضمن السجل
        # هنا سنعتمد على إرساله ضمن السجل إذا كان فارغًا، أو مع أول رسالة
        # أو الأفضل: نستخدم send_message مع الـ prompt الكامل (إذا لم نستخدم start_chat)

        # الطريقة الأبسط: إرسال الـ prompt الكامل مرة واحدة (بدون استخدام start_chat)
        full_prompt_to_send = system_prompt + "\n\n--- سجل المحادثة الأخير ---\n"
        for msg in gemini_history:
           full_prompt_to_send += f"{'أنا' if msg['role'] == 'user' else 'كيوري'}: {msg['parts'][0]['text']}\n"
        full_prompt_to_send += f"أنا: {user_prompt}\nكيوري:" # نطالب النموذج بإكمال الرد

        print(f"DEBUG (get_ai_text): Sending combined prompt to generate_content...")

        response = model.generate_content(
             full_prompt_to_send, # استخدام الـ prompt المدمج
             generation_config=generation_config,
             safety_settings=safety_settings
        )

        # --- معالجة الرد ---
        if not response.parts:
            print(f"WARN (get_ai_text): Gemini response has no parts. Prompt block reason: {response.prompt_feedback.block_reason if response.prompt_feedback else 'N/A'}")
            # قد يكون الرد محجوبًا بسبب إعدادات السلامة
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 final_response_text = f"أعتذر، لا أستطيع الرد على هذا الطلب بسبب قيود السلامة. 😅 [{response.prompt_feedback.block_reason}]"
            else:
                 final_response_text = "أعتذر حبيبتي، لم أتمكن من إنشاء رد مناسب حاليًا. 😅"
        else:
            final_response_text = response.text.strip()
            print(f"DEBUG (get_ai_text): Received AI text response (first 300 chars): {final_response_text[:300]}...")
            # تنظيف أي علامات قد يضيفها النموذج بالخطأ
            final_response_text = final_response_text.replace("[SHOW_EXAMPLES]", "")

    except StopCandidateException as stop_ex:
        print(f"WARN (get_ai_text): Gemini response stopped. Reason: {stop_ex}")
        final_response_text = "أعتذر، لا أستطيع إكمال الرد حاليًا. 😅"
    except Exception as e:
        print(f"ERROR in get_ai_text_response: {e}\n{traceback.format_exc()}", file=sys.stderr)
        final_response_text = "أعتذر فديتج، واجهت مشكلة تقنية بسيطة 😖 حاولي مرة ثانية."

    return final_response_text

# --- 7. Session State Initialization ---
if "chat_history" not in st.session_state:
    print("--- Initializing chat history in session state ---")
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": {
                "text": "يا هلا فيج! أنا كيوري ✨ مستشارتج للأناقة في قطر. شلون أقدر أساعدج اليوم؟ تبين نصيحة، فكرة، أو تشوفين أمثلة؟"
            }
        }
    ]
elif not isinstance(st.session_state.chat_history, list):
     print("--- WARN: Chat history in session state is not a list, reinitializing ---")
     st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": {
                "text": "يا هلا فيج مرة ثانية! ✨ شكل المحادثة السابقة ضاعت، نبدأ من جديد؟"
            }
        }
    ]

# --- 8. Main UI ---
st.title("كيوري ✨ Qurate")
st.caption("رفيقتج وخبيرة أناقتج في قطر")

# استخدام حاوية لضمان ترتيب العناصر
chat_container = st.container(height=500, border=False) # تحديد ارتفاع للحاوية لجعلها قابلة للتمرير

# --- Display Chat History ---
with chat_container:
    if isinstance(st.session_state.chat_history, list):
        print("\n--- Rendering Chat History ---")
        for i, message_data in enumerate(st.session_state.chat_history):
            if isinstance(message_data, dict):
                role = message_data.get("role", "unknown")
                content = message_data.get("content", {}) # الحصول على القاموس أو قاموس فارغ

                # --- استخلاص النص والمنتجات ---
                message_text = ""
                products_to_display = []

                if isinstance(content, str): # التعامل مع الحالة التي قد يكون فيها المحتوى نصًا فقط
                    message_text = content
                elif isinstance(content, dict):
                    message_text = content.get("text", "") # الحصول على النص من القاموس
                    products_to_display = content.get("products", []) # الحصول على المنتجات
                    if not isinstance(products_to_display, list): # التأكد من أنها قائمة
                         print(f"WARN (Render): Products data for msg {i} is not a list, type: {type(products_to_display)}. Resetting.")
                         products_to_display = []
                else:
                    print(f"WARN (Render): Content for msg {i} is neither str nor dict: {type(content)}. Skipping content.")
                    continue # تخطي هذه الرسالة إذا كان المحتوى غير معروف

                # --- طباعة تشخيصية محسنة ---
                print(f"Message {i}: Role={role}, Type(Content)={type(content)}")
                if isinstance(content, dict): print(f"  Content Keys: {list(content.keys())}")
                print(f"  Displaying Text (first 100): {message_text[:100]}...")
                print(f"  Checking Products: Is list? {isinstance(products_to_display, list)}. Length: {len(products_to_display)}")

                # --- عرض الرسالة ---
                avatar_emoji = "👤" if role == "user" else "✨"
                try:
                    with st.chat_message(name=role, avatar=avatar_emoji):
                        # عرض النص أولاً إذا كان موجوداً
                        if message_text:
                            st.markdown(message_text, unsafe_allow_html=False) # تجنب HTML غير الآمن

                        # --- عرض أمثلة المنتجات إذا كانت موجودة ---
                        if products_to_display: # يكفي التحقق من أنها ليست فارغة (تم التأكد أنها قائمة أعلاه)
                            print(f"  Attempting to display {len(products_to_display)} products for message {i}...")
                            st.markdown("---") # فاصل قبل المنتجات

                            # استخدام أعمدة لتنسيق أفضل (اختياري)
                            # num_columns = min(len(products_to_display), 2) # عرض في عمودين كحد أقصى
                            # cols = st.columns(num_columns)

                            for idx, product in enumerate(products_to_display[:MAX_EXAMPLE_PRODUCTS]):
                                # current_col = cols[idx % num_columns] # اختيار العمود الحالي
                                # with current_col: # عرض المنتج داخل العمود
                                    if isinstance(product, dict):
                                        image_url = product.get("image_url")
                                        product_name = product.get("name", "اسم غير متوفر")
                                        product_price_num = product.get("price") # قد يكون رقمًا أو NaN
                                        product_brand = product.get("brand", "") # افترض أنه نص، قد يكون فارغًا
                                        product_store = product.get("store", "") # افترض أنه نص
                                        product_link = product.get('product_url') # الرابط

                                        # تنسيق السعر باستخدام الدالة المساعدة
                                        product_price_str = format_price(product_price_num)

                                        # --- عرض الصورة (مع التصحيح والتحقق) ---
                                        if image_url and isinstance(image_url, str) and image_url.startswith('http'):
                                            # <<<!!! التصحيح الهام للمسافة البادئة هنا !!!>>>
                                            try:
                                                st.image(image_url, width=150, caption=f"{product_name[:30]}...") # عرض اسم قصير تحت الصورة
                                            except Exception as img_err:
                                                print(f"ERROR (Render): Failed to load image {image_url} for product {product_name}. Error: {img_err}")
                                                st.caption(f"(خطأ في تحميل الصورة)") # رسالة خطأ للمستخدم
                                        else:
                                             print(f"WARN (Render): Missing or invalid image_url for product {product_name}: {image_url}")
                                             # يمكنك عرض صورة placeholder إذا أردت
                                             # st.image("placeholder.png", width=150, caption="صورة غير متوفرة")


                                        # --- عرض التفاصيل النصية ---
                                        details = f"**{product_name}**" # اسم المنتج بخط عريض
                                        if product_brand and pd.notna(product_brand): details += f"\n\n*الماركة:* {product_brand}"
                                        if product_price_str != "السعر غير متوفر": details += f"\n\n*السعر:* {product_price_str}"
                                        if product_store and pd.notna(product_store): details += f"\n\n*المتجر:* {product_store}"
                                        st.markdown(details, unsafe_allow_html=False)

                                        # --- عرض زر الرابط ---
                                        if product_link and isinstance(product_link, str) and product_link.startswith('http'):
                                            st.link_button("🛒 الذهاب للمنتج", product_link, type="secondary", use_container_width=True)
                                        else:
                                            print(f"WARN (Render): Missing or invalid product_url for product {product_name}: {product_link}")

                                        st.markdown("---") # فاصل بعد كل منتج

                                    else:
                                        # هذا لا يجب أن يحدث إذا كان get_random_product_examples يعمل بشكل صحيح
                                        print(f"WARN (Render): Encountered non-dict item in products_to_display list for msg {i}: {product}")
                                        st.caption("بيانات منتج غير صالحة")

                except Exception as display_err:
                     print(f"ERROR (Render): Failed displaying message {i}. Role={role}. Error: {display_err}")
                     traceback.print_exc()
                     st.error(f"حدث خطأ أثناء عرض الرسالة رقم {i}. قد تحتاج لتحديث الصفحة.")
            else:
                # هذا لا يجب أن يحدث إذا كان السجل دائمًا قائمة من القواميس
                print(f"WARN (Render): Skipping item in chat_history, not a dict: {message_data}")
        print("--- Finished Rendering Chat History ---")
    else:
         print("ERROR (Render): st.session_state.chat_history is not a list!")
         st.error("خطأ في سجل المحادثة. يرجى تحديث الصفحة.")

# --- User Input Field ---
# استخدام مفتاح ثابت لضمان استمرارية الحالة
user_prompt = st.chat_input("دردشي مع كيوري، اطلبي نصيحة، أو أمثلة (مثل: وريني عبايات سوداء)...", key="chat_input_main")

# --- Process User Input and Generate Response ---
if user_prompt:
    print(f"\n--- Processing User Input: '{user_prompt}' ---")
    # 1. Add user message to history IMMEDIATELY for display
    st.session_state.chat_history.append({"role": "user", "content": user_prompt}) # المحتوى هنا نص فقط

    # --- إعادة رسم الواجهة فورًا لعرض رسالة المستخدم ---
    # هذا يعطي شعوراً أسرع بالاستجابة
    # st.rerun() # -> نؤجل الـ rerun إلى ما بعد الحصول على رد المساعد

    # 2. Determine intent and prepare data for response
    intent = "general_query" # Default intent
    product_examples = []
    show_examples_flag = False

    # تحديد نية عرض الأمثلة أولاً (قد تكون أكثر تحديداً)
    example_keywords = ['مثال', 'أمثلة', 'ورني', 'أرني', 'عطني فكرة', 'اشوف', 'ابي اشوف', 'ابغي اشوف', 'ورينا', 'صور', 'ستايلات','روني','اعرض','example', 'examples', 'show me', 'see', 'ideas for', 'styles of', 'pictures of', 'images of', 'view', 'display']# كلمات إنجليزية مضافة]
    if any(keyword in user_prompt.lower() for keyword in example_keywords):
        if not products_db.empty:
            intent = "show_examples"
            show_examples_flag = True
            print("INFO (Processing): Intent detected as 'show_examples'.")
            # استدعاء دالة جلب الأمثلة
            product_examples = get_random_product_examples(user_prompt, products_db, num_examples=MAX_EXAMPLE_PRODUCTS)
            print(f"DEBUG (Processing): get_random_product_examples returned {len(product_examples)} items.")
            if product_examples:
                print(f"  Example product 1 keys: {list(product_examples[0].keys())}")
        else:
            print("WARN (Processing): 'show_examples' intent detected, but product database is empty.")
            # قد نرغب في إخبار المستخدم بأن الأمثلة غير متوفرة حالياً

    # إذا لم تكن نية عرض الأمثلة، تحقق من نية اقتراح الصالونات
    elif suggest_salons(user_prompt): # استدعاء الدالة مباشرة للتحقق
         intent = "salon_suggestion"
         print("INFO (Processing): Intent detected as 'salon_suggestion'.")
         # لا نحتاج لجلب الاقتراحات هنا، سنفعل ذلك عند بناء الرد إذا لزم الأمر

    else:
        intent = "general_query"
        print("INFO (Processing): Intent defaulted to 'general_query'.")


    # 3. Get AI text response (always get text, regardless of examples)
    assistant_final_text = "أفكر لج بأحلى رد... 🤔" # نص مؤقت
    with st.spinner(assistant_final_text):
         # نمرر فقط السجل قبل إضافة رسالة المستخدم الأخيرة (أو السجل الكامل إذا كان النموذج يعالج هذا)
         # نرسل السجل حتى الرسالة *قبل* رسالة المستخدم الحالية للحصول على رد مناسب
         ai_text_response = get_ai_text_response(user_prompt, st.session_state.chat_history[:-1])


    # 4. Build the final assistant message content dictionary
    assistant_message_content = {"text": ai_text_response} # ابدأ دائمًا بالنص

    # إضافة بيانات إضافية بناءً على النية
    if intent == "salon_suggestion":
        suggested_salon_list = suggest_salons(user_prompt) # احصل على الاقتراحات الآن
        if suggested_salon_list:
            # يمكنك دمج الاقتراحات في النص مباشرة أو إضافتها كبيانات منفصلة للعرض
            # هنا ندمجها في النص كأبسط حل لـ MVP
            salons_text = "\n\nبالنسبة للصالونات، هذي بعض الأماكن المعروفة اللي ممكن تشيكين عليها:\n" + "\n".join([f"- {s}" for s in suggested_salon_list])
            assistant_message_content["text"] += salons_text
            print(f"DEBUG (Processing): Appended {len(suggested_salon_list)} salon suggestions to AI text.")

    elif intent == "show_examples" and show_examples_flag and product_examples:
        # إضافة المنتجات فقط إذا كانت النية صحيحة والعينات موجودة
        assistant_message_content["products"] = product_examples[:MAX_EXAMPLE_PRODUCTS]
        print(f"DEBUG (Processing): Adding {len(product_examples)} products to assistant message content.")
    elif intent == "show_examples" and not product_examples:
        # إذا طلب المستخدم أمثلة ولم نجدها
        assistant_message_content["text"] += "\n\nحاولت أدور لج أمثلة بس للأسف ما لقيت شي مناسب لطلبج الحين 😔 يمكن تجربين توصيف ثاني؟"
        print("DEBUG (Processing): No product examples found, added clarification text.")


    print(f"DEBUG (Processing): Final assistant_message_content keys: {list(assistant_message_content.keys())}")

    # 5. Add the complete assistant response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_message_content})

    # 6. Rerun the script to update the UI with the new messages
    print("--- Rerunning Streamlit app to update UI ---")
    st.rerun()

# --- 9. Sidebar ---
with st.sidebar:
    # --- Logo or Title ---
    try:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=120)
        else:
            st.header("كيوري ✨")
            print("INFO (Sidebar): Logo file not found, displaying text header.")
    except Exception as e:
        st.header("كيوري ✨")
        print(f"ERROR (Sidebar): Error rendering sidebar logo: {e}")

    st.markdown("---")
    st.subheader("عن كيوري")
    st.caption("رفيقتج وخبيرة أناقتج في قطر 💖\n_(نسخة تجريبية أولية - MVP)_")
    st.markdown("---")

    # --- Clear Chat Button ---
    if st.button("مسح المحادثة الحالية", key="clear_chat_button", type="primary", use_container_width=True):
        print("--- Action: Clearing chat history ---")
        # إعادة تعيين برسالة ترحيبية جديدة
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": {
                    "text": "يا هلا فيج من جديد! ✨ صفحة يديدة، شنو بخاطرج؟"
                }
            }
        ]
        st.rerun() # تحديث الواجهة فورًا

    st.markdown("---")
    st.caption("© 2025 Qurate")
# --- END OF FILE qurate.py ---
