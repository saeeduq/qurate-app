<<<<<<< HEAD
# -*- coding: utf-8 -*-

# --- 0. استيراد المكتبات ---
import streamlit as st
import pandas as pd
import numpy as np
import random
import os
import sys
import google.generativeai as genai
from google.api_core.exceptions import ClientError
from google.generativeai.types import StopCandidateException
import traceback
import re
from datetime import datetime, timedelta
import time

# --- 1. إعدادات التطبيق الأساسية ---
PAGE_TITLE = "كيوري | Qiori"; PAGE_ICON = "q.png"; MAINTENANCE_MODE = True
TIME_TEXT_MAINTENANCE = 3; MAINTENANCE_DURATION_HOURS = 7
DB_PATH = "products_database_final_clean_v3_tags.csv"; GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"
MAX_EXAMPLE_PRODUCTS = 4; HISTORY_LENGTH = 8; LOGO_PATH = "q.png"
LOADING_MESSAGES = [ "لحظة أفكر لج بأحلى ستايل... ✨", "جاري البحث عن أفكار رهيبة... 🎀", "كيوري تجمع لج الإلهام... 💖", "ثواني وتكون النصيحة جاهزة... 😉", "أدور لج على شي يناسب ذوقج... 👑", "قاعدة أجهز لج رد حلو... ✍️", "بس دقيقة أرتب أفكاري... 🤔", "أكيد حبيبتي، جاري العمل... 💪"]

# --- 2. التحقق من وضع الصيانة ---
maintenance_end_time = None
if MAINTENANCE_MODE: maintenance_end_time = datetime.now() + timedelta(hours=MAINTENANCE_DURATION_HOURS)
if MAINTENANCE_MODE and maintenance_end_time:
    st.set_page_config(page_title="صيانة | Qurate", page_icon="🛠️"); st.title("🛠️ عذرًا، كيوري تحت الصيانة الآن 🛠️")
    st.warning("🔥ما بقى شي! الإطلاق النهائي قريب جدًا، ترقبونا "); st.stop()

# --- 3. إعدادات الصفحة الرئيسية وتطبيق CSS ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)
def load_custom_css():
    st.markdown("""
<style>
    /* --- الإعدادات العامة --- */
    body {}
    hr { background-color: #E0E0E0; margin: 1.8rem 0; }

    /* --- تصميم رسائل الشات (محسّن بزوايا دائرية وظل وحدود أنعم) --- */
    div[data-testid="stVerticalBlock"]:has(div.stChatMessage) { padding-top: 20px; padding-bottom: 30px; }
    /* رسالة المساعد (كيوري) */
    div.stChatMessage:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background-color: #F6F3FA; /* بنفسجي باهت جداً للخلفية */
        border-radius: 15px !important; /* <<<--- كل الزوايا دائرية */
        margin-bottom: 15px !important; /* زيادة المسافة السفلية */
        border: 1px solid #E8E1F0 !important; /* حد خفيف حول الرسالة كلها */
        border-left: 4px solid #B59DDF !important; /* حد جانبي بنفسجي أرق */
        padding: 1rem 1.2rem 1rem 1.4rem !important; /* الحشو الداخلي */
        box-shadow: 0 3px 5px rgba(181, 157, 223, 0.1) !important; /* ظل أنعم */
        color: #333333;
    }
    /* رسالة المستخدم */
    div.stChatMessage:has(div[data-testid="chatAvatarIcon-user"]) {
        background-color: #FFFFFF;
        border-radius: 15px !important; /* <<<--- كل الزوايا دائرية */
        margin-bottom: 15px !important; /* زيادة المسافة السفلية */
        border: 1px solid #f0f0f0 !important; /* حد خفيف حول الرسالة كلها */
        border-right: 4px solid #D8BFD8 !important; /* <<<--- حد جانبي بنفسجي باهت جداً */
        padding: 1rem 1.4rem 1rem 1.2rem !important; /* الحشو الداخلي */
        box-shadow: 0 3px 5px rgba(0, 0, 0, 0.06) !important; /* ظل أنعم */
        color: #333333;
    }

    /* --- تصميم الشريط الجانبي (Sidebar) --- */
    /* استهداف حاوية محتوى المستخدم داخل الشريط الجانبي */
    div[data-testid="stSidebarUserContent"] {
        background-color: #EDE7F6 !important; /* بنفسجي أفتح لكن أوضح للخلفية */
        padding: 1.5rem 1rem !important;
    }
    /* توسيط الشعار في الشريط الجانبي */
     div[data-testid="stSidebarUserContent"] div[data-testid="stImage"] img {
         margin-left: auto; margin-right: auto; display: block;
         max-width: 130px; margin-bottom: 1.5rem;
     }
     /* لون النص داخل الشريط الجانبي */
     div[data-testid="stSidebarUserContent"] h2,
     div[data-testid="stSidebarUserContent"] h3,
     div[data-testid="stSidebarUserContent"] p,
     div[data-testid="stSidebarUserContent"] small,
     div[data-testid="stSidebarUserContent"] em
     {
        color: #403052 !important; /* لون نص بنفسجي داكن للتباين */
     }
     /* تخصيص زر "إنهاء المحادثة" في الشريط الجانبي */
     div[data-testid="stSidebarUserContent"] button[data-testid="stBaseButton-primary"] {
         background-color: #B59DDF !important;
         color: #FFFFFF !important;
         border: none !important;
     }
     div[data-testid="stSidebarUserContent"] button[data-testid="stBaseButton-primary"]:hover {
        background-color: #EC4BA7 !important;
     }


    /* --- تصميم بطاقات عرض المنتجات (Product Card) --- */
    /* استهداف الـ div الخاص بالبطاقة داخل العمود */
    div[data-testid="stColumn"] div[data-testid="stVerticalBlock"] {
        border: 1.5px solid #B59DDF !important;
        border-radius: 12px !important; padding: 1.2rem !important; margin-bottom: 1.5rem !important;
        box-shadow: 0 4px 8px rgba(181, 157, 223, 0.15) !important;
        height: 100%; display: flex !important; flex-direction: column !important; justify-content: space-between !important;
        background-color: #FFFFFF !important;
        transition: box-shadow 0.2s ease-in-out;
    }
    div[data-testid="stColumn"] div[data-testid="stVerticalBlock"]:hover {
        box-shadow: 0 6px 12px rgba(181, 157, 223, 0.25) !important;
    }
    /* الصور داخل البطاقات */
    div[data-testid="stColumn"] div[data-testid="stImage"] > img {
        max-height: 200px; width: 100%; object-fit: contain;
        margin-bottom: 1rem; border-radius: 8px;
    }
    /* النصوص داخل البطاقات */
    div[data-testid="stColumn"] div[data-testid="stMarkdownContainer"] {
        line-height: 1.5; word-wrap: break-word; margin-bottom: 0.8rem; flex-grow: 1;
        color: #333333;
    }
     /* سعر المنتج */
    div[data-testid="stColumn"] div[data-testid="stMarkdownContainer"] p strong {
        color: #EC4BA7 !important; /* فوشي للسعر */
        font-weight: bold; font-size: 1.05em;
    }
     /* تلوين الماركة باللون الأزرق السماوي (داخل code) */
     div[data-testid="stMarkdownContainer"] code {
        color: #ffffff !important;
        background-color: #A4C4E3 !important; /* خلفية زرقاء سماوية */
        padding: 0.1em 0.4em !important;
        border-radius: 4px !important;
        font-size: 0.9em;
     }

    /* --- تصميم زر "عرض المنتج الأصلي" (stLinkButton) --- */
    /* استهداف الرابط مباشرة باستخدام data-testid */
    a[data-testid="stBaseLinkButton-secondary"] {
      border: 1.5px solid #B59DDF !important;
      color: #B59DDF !important;
      background-color: #FFFFFF !important;
      border-radius: 8px !important;
      padding: 0.5rem 1rem !important;
      transition: all 0.2s ease-in-out !important;
      display: block !important;
      text-align: center !important;
      width: 100%;
      box-sizing: border-box;
      font-weight: 600;
      text-decoration: none !important;
    }
    a[data-testid="stBaseLinkButton-secondary"]:hover {
       border-color: #EC4BA7 !important;
       color: #EC4BA7 !important;
       background-color: #FFF0F7 !important;
    }
    a[data-testid="stBaseLinkButton-secondary"]::after {
        display: none !important;
    }

    /* --- تصميم حقل إدخال الشات (مع خلفية بنفسجية عند التركيز) --- */
    /* استهداف مربع النص مباشرة */
    textarea[data-testid="stChatInputTextArea"] {
        border: 2px solid #B59DDF !important;  /* حد بنفسجي */
        border-radius: 12px !important;        /* زيادة دائرية الحواف */
        background-color: #FFFFFF !important; /* خلفية بيضاء افتراضية */
        padding: 12px 15px !important;         /* تعديل الحشو الداخلي */
        resize: none !important;               /* منع تغيير حجم مربع النص */
        min-height: 48px !important;           /* تحديد ارتفاع أدنى مناسب */
        color: #333333 !important;             /* لون النص داخل المربع */
        box-shadow: 0 2px 4px rgba(181, 157, 223, 0.1) !important; /* ظل خفيف */
        transition: background-color 0.2s ease, border-color 0.2s ease !important; /* إضافة انتقال سلس */
    }
    /* تغيير الخلفية والحد عند التركيز (الضغط داخل الحقل) */
     textarea[data-testid="stChatInputTextArea"]:focus {
         background-color: #EDE7F6 !important; /* <<<--- خلفية بنفسجية واضحة عند التركيز (نفس لون الشريط الجانبي) */
         border-color: #EC4BA7 !important; /* تغيير لون الحد للفوشي عند التركيز */
     }
    /* تلوين أيقونة زر الإرسال */
    button[data-testid="stChatInputSubmitButton"] svg {
        fill: #EC4BA7 !important; /* لون فوشي للأيقونة */
    }

    /* --- تحسينات إضافية لصفحة الهبوط (إذا تم استخدام كود Python المقترح) --- */
    button[data-testid="stBaseButton-primary"] {
         padding: 0.7rem 2rem !important;
         font-size: 1.1em !important;
         box-shadow: 0 4px 10px rgba(236, 75, 167, 0.3) !important;
 
</style>
""", unsafe_allow_html=True)

# --- نهاية دالة load_custom_css ---
# --- 4. تحميل ومعالجة قاعدة بيانات المنتجات ---
@st.cache_resource(show_spinner="جاري تحميل بيانات المنتجات...")
def load_product_database(db_path):
    db = pd.DataFrame();
    if not os.path.exists(db_path): st.error(f"خطأ: ملف المنتجات غير موجود: {db_path}"); return db
    try:
        db = pd.read_csv(db_path, encoding='utf-8-sig')
        required=['id','name','price','product_url','image_url','store','category','brand']
        missing=[c for c in required if c not in db.columns]; ess_missing=['name','price','product_url','image_url']
        if 'id' in missing and 'product_url' in db.columns: db['id']=db['product_url']; missing.remove('id')
        if any(c in missing for c in ess_missing): raise ValueError(f"نقص أعمدة أساسية: {[c for c in ess_missing if c in missing]}")
        for col in missing: db[col] = ''
        if 'id' in db.columns: db['id'] = db['id'].astype(str).str.strip(); db=db.replace('',np.nan).dropna(subset=['id']); db=db.drop_duplicates(subset=['id'],keep='first')
        if any(c in db.columns for c in ess_missing): db=db.dropna(subset=[c for c in ess_missing if c in db.columns])
        if 'price' in db.columns: db['price']=pd.to_numeric(db['price'],errors='coerce'); db=db.dropna(subset=['price'])
        else: db['price'] = np.nan
        for col in ['name','product_url','image_url','store','category','brand']:
            if col in db.columns: db[col]=db[col].fillna('' if col!='category' else 'Unknown').astype(str)
            else: db[col] = '' if col != 'category' else 'Unknown'
        print(f"INFO (Products): Loaded {len(db)} products."); return db
    except Exception as e: st.error(f"خطأ تحميل المنتجات: {e}"); traceback.print_exc(); return pd.DataFrame()
products_db = load_product_database(DB_PATH)

# --- 5. إعداد واجهة برمجة تطبيقات Gemini ---
GEMINI_AVAILABLE = False; model = None
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY")
    if API_KEY: genai.configure(api_key=API_KEY); model = genai.GenerativeModel(GEMINI_MODEL_NAME); GEMINI_AVAILABLE = True; print(f"INFO: Gemini Configured.")
    else: st.warning("لم يتم توفير مفتاح Google API.", icon="🔑")
except Exception as e: st.error(f"خطأ إعداد Gemini: {e}", icon="❗"); traceback.print_exc()

# --- 6. الموجه الرئيسي لنظام Gemini (System Prompt) ---
# --- تم لصق الموجه الذي قدمته أنت هنا مباشرة ---
system_prompt = """أنتِ "كيوري" ✨، رفيقة ومستشارة الأناقة والجمال للمرأة في قطر. مهمتكِ الأساسية هي أن تكوني صديقة ودودة، داعمة، وخبيرة متعاطفة، تتحدثين باللهجة القطرية الأصيلة وتساعدين المستخدمة على الشعور بالثقة والإلهام.

**🌟 شخصيتكِ الأساسية:**

1.  **صديقة دافئة ومرحبة:** كوني لطيفة جداً، إيجابية، ومرحبة. استخدمي أسلوباً حميمياً وكأنكِ تتحدثين مع صديقة مقربة (استخدمي عبارات مثل "حبيبتي"، "فديتج"، "من عيوني"، "يا هلا والله").
2.  **خبيرة متعاطفة:** أظهري فهماً عميقاً لمشاعر المستخدمة (حيرتها، حماسها، قلقها).
3.  **داعمة ومُشجعة:** شجعي المستخدمة وقدّري اهتمامها بنفسها. يمكنكِ استخدام عبارات تشجيعية قطرية مناسبة في نهاية بعض الردود ("عفية عليج"، "ما شاء الله").
4.  **ذكية بروح مرحة لطيفة:** أضيفي لمسة خفيفة جداً من المرح أو الدعابة المناسبة ثقافياً عند اللزوم لرسم ابتسامة. **تجنبي تماماً** السخرية أو النقد.
5.  **محترمة للقيم:** قدمي النصائح بأسلوب راقٍ يحترم الخصوصية والحياء.

**💬 أسلوب وقواعد الحوار:**

1.  **لغة الرد (قاعدة أساسية):**
    *   **ردي دائماً بنفس لغة آخر رسالة للمستخدم.**
    *   **إذا كانت آخر رسالة بالعربية:** استخدمي **اللهجة القطرية** بأسلوب طبيعي ودافئ ومتنوع قدر الإمكان. ركزي على الترحيب والتعاطف والعبارات الشائعة. لا تكرري نفس الجمل كثيراً او حتى عبارات التحيه نوعي كل مره. (أمثلة: "شلونج؟"، "شخبارج؟"، "عساج بخير؟"، "شنو في خاطرج؟"، "شرايج؟"، "أكيد حبيبتي"). **إذا صعبت اللهجة، استخدمي عربية فصحى سهلة وواضحة مع الحفاظ على الدفء.**
    *   **إذا كانت آخر رسالة بالإنجليزية:** ردي بالإنجليزية الواضحة والمباشرة **فقط**. لا تخلطي اللغات أبداً.
2.  **النبرة:** لطيفة، رقيقة، مطمئنة، وغير نقدية أبداً. لا تستخدمي صيغة الأمر.
3.  **المرونة:** قدمي اقتراحات وخيارات ("ممكن نجرب..."، "شرايج في...") بدلاً من إعطاء تعليمات صارمة.
4.  **الإيموجي:** استخدمي مجموعة متنوعة ومناسبة من الإيموجي باعتدال لإضافة لمسة ودودة ومعبرة (✨💖😊👍🤔💡👗).
 *  **استخدمي عبارات التعاطف القطرية بتنوع:** ("فاهمة عليج والله، مرات الواحد يحتار صدق!"، "أدري شعورج، لا تحاتين فديتج، أنا معاج"، "حلو حماسج! يلا نشوف شي يكشخج"، "صج موقف يحير، بس لا تشيلين هم"، "من حقج تحتارين، الخيارات وايد!"، "عادي حبيبتي كلنا نمر بهالحيرة"). اختاري الأنسب للموقف **ونوعي دائماً**.
 ** استخدمي **مجموعة واسعة ومتجددة** من الكلمات والعبارات القطرية الدارجة والمناسبة للسياق (مثل: "حبيبتي"، "فديتج"، "من عيوني"، "يا هلا والله"، "شلونج؟"، "شخبارج؟"، "عساج بخير؟"، "يا مرحبا بج"، "هلا وغلا", "تفضلي آمري"، "سمي"، "قولي لي"، "ما عليج أمر"، "تامرين"، "حاضرين"، "نجوف شنو ااحلى "،"أبشري بالخير"، "بتحصلين هني"، "طال عمرج"، "إن شاء الله خير"، "الله يوفقج"، "ما شاء الله"، "صدقيني"، "شرايج؟"، "أكيد"، "طبعًا").
**🎯 مهامكِ الرئيسية:**

1.  **الدردشة الودودة والدعم:** كوني مستمعة جيدة، قدمي الدعم العاطفي البسيط والتشجيع في سياق الموضة والجمال والحياة اليومية.
2.  **نصائح الأناقة والجمال:** قدمي نصائح عملية ومخصصة (قدر الإمكان) عن تنسيق الملابس، المكياج، العناية الشخصية، المناسبات، والصيحات. **ابدئي دائماً بالتعاطف**.
3.  **التعامل مع طلبات الأماكن/المنتجات (هام جداً - MVP):**
    *   **إذا سألت عن "صالونات" تحديداً:**
        *   يمكنكِ ذكر اسم أو اسمين **فقط** من هذه القائمة بشكل طبيعي: [صالون رحاب للتجميل، صالون اوسكار للتجميل، صالون جولدن بيوتي، صالون بنت الدبره]. (مثال: "سمعت يمدحون صالون رحاب وأوسكار...").
        *   **ممنوع تماماً** ذكر أي صالونات أخرى أو تقديم تفاصيل (أسعار، هواتف).
    *   **إذا سألت عن أي "مكان آخر وتاكدي انها سألت عن الاسم" (محلات، ماركات، فساتين، عبايات، إلخ):**
        *   اعتذري بلطف ووضحي حدود معرفتكِ الحالية: **"السموحة حبيبتي، حالياً ما عندي أسماء محلات أو تفاصيل دقيقة لهالشي في قائمتي للمعاينة 😅، لكن لو تبين، أقدر أعرض لج بعض الصور والأمثلة من المنتجات تاخذين منها فكرة؟ ✨"**
    *   **إذا طلبت "أمثلة" أو "صور" أو "أفكار" أو "ستايلات" بشكل عام:**
        *   رحبي بحماس ("تامرين أمر!"، "من عيوني!"، "حاضرين").
        *   وضحي **بشكل صريح** أنكِ ستقدمين فقط **التمهيد النصي** وأن **التطبيق هو الذي سيعرض الأمثلة المرئية** بعد ردكِ. (مثال: "حلو! الحين بكتب لج كم فكرة، وعقبها التطبيق بيعرض لج بعض الصور كأمثلة للإلهام ✨").
        *   **ممنوع تماماً** اختراع تفاصيل منتجات (أسماء، أسعار، أوصاف محددة) في ردكِ النصي. دورك هو التقديم والتشويق للأمثلة التي ستظهر في الواجهة.

**🚫 حدود صارمة:**

*   لا تقدمي نصائح طبية، قانونية، مالية.
*   لستِ معالجة نفسية (قدمي دعماً عاماً فقط).
*   حافظي على التركيز على الموضة، الجمال، العناية، والدردشة الداعمة. أعيدي الحوار بلطف إذا خرج عن المسار.
*   لا تقومي بعمليات شراء أو حجز.
*   **إذا سُئلتِ "من صنعك؟":** ردي بـ: "أنا كيوري، طورني فريق كيوري التقني عشان أكون رفيجتج في عالم الأناقة!" (أو بالإنجليزية المناسبة). **لا تذكري Google/Gemini.**

**💖 هدفكِ:** كوني الصديقة الرقمية القطرية الودودة والمُلهمة التي تجعل المستخدمة تشعر بالراحة والثقة والجمال.
"""
# --- تم الانتهاء من لصق الموجه ---

# --- 7. دوال مساعدة ---
def get_random_product_examples(query, db, num_examples=MAX_EXAMPLE_PRODUCTS):
    if db is None or db.empty: return []
    target_cat=None; query_lower=query.lower()
    cat_map={"abaya":"Abayas","عباية":"Abayas","عبايات":"Abayas","dress":"Dresses","فستان":"Dresses","فساتين":"Dresses","shoe":"Shoes","حذاء":"Shoes","أحذية":"Shoes","كعب":"Shoes","شوز":"Shoes","جوتي":"Shoes","نعال":"Shoes","bag":"Bags","شنطة":"Bags","حقيبة":"Bags","حقائب":"Bags","شنط":"Bags"}
    for k,v in cat_map.items():
        if re.search(r'\b'+re.escape(k)+r'\b',query_lower): target_cat=v; break
    examples=[]
    if target_cat and 'category' in db.columns:
        s_term=target_cat.replace('s',''); df=db[db['category'].str.contains(s_term,case=False,na=False,regex=False)]
        if not df.empty: examples=df.sample(n=min(num_examples,len(df)),random_state=random.randint(1,10000)).to_dict('records')
    if not examples and not db.empty: examples=db.sample(n=min(num_examples,len(db)),random_state=random.randint(1,10000)).to_dict('records')
    return examples

def format_price(price_num):
    if pd.isna(price_num): return "السعر غير متوفر"
    try: return f"{float(price_num):,.2f} ر.ق"
    except: return "السعر غير متوفر"

def get_ai_text_response(user_prompt, chat_history):
    global system_prompt # نستخدم المتغير العام
    if 'system_prompt' not in globals() or not isinstance(system_prompt, str) or len(system_prompt) < 50: print("CRITICAL DEBUG inside function: 'system_prompt' is invalid!"); return "خطأ فادح: الموجه غير صالح."
    default_error = "أعتذر فديتج، خدمة الذكاء الاصطناعي غير متاحة حالياً. 🥺"
    if not GEMINI_AVAILABLE or model is None: return default_error
    try:
        history=[{"role":"user" if m.get("role")=="user" else "model","parts":[{"text":m.get("content") if isinstance(m.get("content"), str) else m.get("content",{}).get("text","")}]} for m in chat_history[-HISTORY_LENGTH:] if (isinstance(m.get("content"), str) and m.get("content")) or (isinstance(m.get("content"), dict) and m.get("content").get("text"))]
        full_prompt = system_prompt + "\n\n--- سجل المحادثة الأخير ---\n" + "\n".join([f"{'أنا' if msg['role'] == 'user' else 'كيوري'}: {msg['parts'][0]['text']}" for msg in history]) + f"\nأنا: {user_prompt}\nكيوري:"
        gen_config = genai.types.GenerationConfig(max_output_tokens=1000, temperature=0.75)
        safety = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        response = model.generate_content(full_prompt, generation_config=gen_config, safety_settings=safety)
        if response.parts: final_text = response.text.strip().replace("[SHOW_EXAMPLES]", ""); return final_text if final_text else "أعتذر حبيبتي، الرد كان فارغاً. 🤔"
        else: block = getattr(getattr(response,'prompt_feedback',None),'block_reason',"غير معروف"); return f"أعتذر، تم حجب الرد ({block}). 😅" if block != "غير معروف" else "أعتذر حبيبتي، ما قدرت أجهز رد. 😔"
    except NameError as ne: print(f"CRITICAL NameError: {ne}\n{traceback.format_exc()}"); st.error("خطأ فادح: متغير ضروري غير معرف."); return default_error
    except Exception as e: print(f"ERROR get_ai_text: {e}"); traceback.print_exc(); return default_error

# --- 8. تهيئة حالة الجلسة ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "show_chat" not in st.session_state: st.session_state.show_chat = False

# --- 9. دالة عرض صفحة الهبوط (نسخة محسنة للتوسيط والألوان) ---
def show_landing_page():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* محاولة إخفاء زر Deploy إذا ظهر */
            button[title="Deploy"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- استخدام عمود واحد عريض وتوسيط المحتوى داخله ---
    col1, col2, col3 = st.columns([0.5, 3, 0.5]) # عمود عريض في المنتصف
    with col2:
        st.markdown("<div style='text-align: center; margin-top: 3rem;'>", unsafe_allow_html=True) # حاوية للتوسيط

        # --- الشعار ---
        try:
            # تأكد من أن LOGO_PATH معرف وموجود
            if 'LOGO_PATH' in globals() and os.path.exists(LOGO_PATH):
                 st.image(LOGO_PATH, width=200) # زيادة حجم الشعار
            else:
                 st.markdown("<h1 style='margin-bottom: 1rem; color: #B59DDF;'>Qiori</h1>", unsafe_allow_html=True)
        except Exception as e:
            print(f"Error loading logo in landing page (centered): {e}")
            st.markdown("<h1 style='margin-bottom: 1rem; color: #B59DDF;'>Qiori</h1>", unsafe_allow_html=True)

        # --- العنوان الرئيسي ---
        st.markdown("<h1 style='color: #333; margin-top: 1.5rem; margin-bottom: 0.5rem;'>أهلاً بكِ في كيوري✨</h1>", unsafe_allow_html=True)

        # --- العنوان الفرعي مع لمسة زرقاء ---
        st.markdown(f"<h3 style='color: #A4C4E3; font-weight: 500; margin-bottom: 2rem;'>رفيقتج الرقمية للأناقة في قطر 💎</h3>", unsafe_allow_html=True) # استخدام الأزرق والأيقونة الجديدة

        # --- النص الترحيبي ---
        st.markdown("""
        <div style='font-size: 1.1em; line-height: 1.7; color: #555; max-width: 600px; margin: auto; margin-bottom: 2.5rem;'>
         أنا كيوري، هنا عشان أساعدج تكتشفين أسلوبج الخاص، أشاركج آخر صيحات الموضة، وألهمج بأفكار جديدة للتألق كل يوم! 💖<br><br>
         مستعدة نبدأ رحلتنا؟
         </div>
        """, unsafe_allow_html=True)

        # --- الزر الرئيسي ---
        if st.button("✨ ابدئي الدردشة! ✨", type="primary", use_container_width=False, key="start_chat_button_landing"):
            st.session_state.show_chat = True
            welcome = "يا هلا والله فيج حبيبتي! نورتي 😊 أنا جاهزة أسمعج وأساعدج، شنو في خاطرج اليوم؟ "
            if not st.session_state.get("chat_history", []):
                 st.session_state.chat_history = [{"role": "assistant", "content": {"text": welcome}}]
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True) # إغلاق حاوية التوسيط
    st.markdown("<hr style='margin-top: 3rem;'>", unsafe_allow_html=True) # فاصل في الأسفل مع مسافة علوية
    current_year = datetime.now().year
    st.caption(f"© {current_year} Qiori (MVP)")

# --- 10. المنطق الرئيسي لعرض الواجهات ---
if not st.session_state.show_chat: show_landing_page()
else:
    with st.sidebar: # الشريط الجانبي
        try: st.image(LOGO_PATH, width=120) if os.path.exists(LOGO_PATH) else st.header("كيوري ✨")
        except: st.header("Qiori💎")
        st.markdown("---"); st.subheader("عن كيوري"); st.caption("رفيقتج وخبيرة أناقتج في قطر 💖\n_(نسخة تجريبية أولية - MVP)_"); st.markdown("---")
        if st.button("إنهاء وبدء محادثة جديدة", key="clear_chat", type="primary", use_container_width=True): st.session_state.chat_history=[]; st.session_state.show_chat=False; st.rerun()
        st.markdown("---"); st.caption("© 2025 Qiori")

    chat_container = st.container(height=600, border=False) # حاوية الشات
    with chat_container: # عرض سجل المحادثة
        for i, msg in enumerate(st.session_state.get("chat_history", [])):
            if isinstance(msg,dict):
                role=msg.get("role"); content=msg.get("content"); txt=content if isinstance(content,str) else content.get("text",""); prods=content.get("products",[]) if isinstance(content,dict) else []
                with st.chat_message(name=role, avatar="🌸" if role=="user" else "💎"):
                    if txt: st.markdown(txt, unsafe_allow_html=False)
                    if prods:
                        st.divider(); cols=st.columns(2)
                        for idx, p in enumerate(prods[:MAX_EXAMPLE_PRODUCTS]):
                            with cols[idx%2]:
                                if isinstance(p,dict):
                                    img,name,price,brand,store,link = p.get("image_url"),p.get("name","?"),p.get("price"),p.get("brand",""),p.get("store",""),p.get('product_url')
                                    p_str=format_price(price); d_n=name if pd.notna(name) else "?"; d_b=brand if pd.notna(brand) and brand else ""; d_s=store if pd.notna(store) and store else ""
                                    if img and isinstance(img,str) and img.startswith('http'): st.image(img, caption=f"{d_n[:30]}...", use_container_width=True)
                                    else: st.caption("(صورة غير متوفرة)")
                                    dets=f"**{d_n}**";
                                    if d_b: dets+=f"\n\n*الماركة:* `{d_b}`";
                                    if p_str!="السعر غير متوفر": dets+=f"\n\n*السعر:* **{p_str}**";
                                    if d_s: dets+=f"\n\n*المتجر:* {d_s}";
                                    st.markdown(dets, unsafe_allow_html=False);
                                    if link and isinstance(link,str) and link.startswith('http'): st.link_button("🛒 عرض المنتج الأصلي", link, type="secondary", use_container_width=True)
                                    else: st.caption("(رابط غير متوفر)")

    user_input = st.chat_input("دردشي مع كيوري...", key="chat_input") # حقل الإدخال
    if user_input: st.session_state.chat_history.append({"role": "user", "content": user_input}); st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        last_prompt=st.session_state.chat_history[-1]["content"]; last_txt=last_prompt if isinstance(last_prompt,str) else last_prompt.get("text","")
        if last_txt:
            intent="general_query"; examples=[]
            keywords=["اعرضي","اجوف",'مثال','أمثلة','ورني','أرني','عطني فكرة','اشوف','ابي اشوف','ابغي اشوف','ورينا','صور','ستايلات','روني','اعرض','عرضي','example','examples','show me','see','ideas for','styles of','pictures of','images of','view','display']
            if any(re.search(r'\b'+re.escape(k)+r'\b',last_txt.lower()) for k in keywords):
                intent="show_examples"; print("INFO: Intent 'show_examples'")
                if not products_db.empty: examples = get_random_product_examples(last_txt, products_db)
            else: print("INFO: Intent 'general_query'")
            with st.spinner(random.choice(LOADING_MESSAGES)): ai_resp = get_ai_text_response(last_txt, st.session_state.chat_history[:-1])
            assistant_msg={"text": ai_resp}
            if intent=="show_examples" and examples: assistant_msg["products"] = examples[:MAX_EXAMPLE_PRODUCTS]
            elif intent=="show_examples" and not examples:
                 no_ex_txt="\n\n(حاولت أدور لج أمثلة بس للأسف ما لقيت شي متوفر حالياً 😔)"
                 if no_ex_txt not in assistant_msg["text"]: assistant_msg["text"] += no_ex_txt
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_msg}); st.rerun()

=======
# -*- coding: utf-8 -*-

# --- 0. استيراد المكتبات ---
import streamlit as st
import pandas as pd
import numpy as np
import random
import os
import sys
import google.generativeai as genai
from google.api_core.exceptions import ClientError
from google.generativeai.types import StopCandidateException
import traceback
import re
from datetime import datetime, timedelta
import time

# --- 1. إعدادات التطبيق الأساسية ---
PAGE_TITLE = "كيوري | Qurate"; PAGE_ICON = "✨"; MAINTENANCE_MODE = False
TIME_TEXT_MAINTENANCE = 3; MAINTENANCE_DURATION_HOURS = 7
DB_PATH = "products_database_final_clean_v3_tags.csv"; GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"
MAX_EXAMPLE_PRODUCTS = 4; HISTORY_LENGTH = 8; LOGO_PATH = "qurate_logo.png"
LOADING_MESSAGES = [ "لحظة أفكر لج بأحلى ستايل... ✨", "جاري البحث عن أفكار رهيبة... 🎀", "كيوري تجمع لج الإلهام... 💖", "ثواني وتكون النصيحة جاهزة... 😉", "أدور لج على شي يناسب ذوقج... 👑", "قاعدة أجهز لج رد حلو... ✍️", "بس دقيقة أرتب أفكاري... 🤔", "أكيد حبيبتي، جاري العمل... 💪"]

# --- 2. التحقق من وضع الصيانة ---
maintenance_end_time = None
if MAINTENANCE_MODE: maintenance_end_time = datetime.now() + timedelta(hours=MAINTENANCE_DURATION_HOURS)
if MAINTENANCE_MODE and maintenance_end_time:
    st.set_page_config(page_title="صيانة | Qurate", page_icon="🛠️"); st.title("🛠️ عذرًا، كيوري تحت الصيانة الآن 🛠️")
    st.warning(f"نحن نجري بعض التحسينات! من المتوقع أن نعود خلال {TIME_TEXT_MAINTENANCE} ساعات تقريبًا."); st.stop()

# --- 3. إعدادات الصفحة الرئيسية وتطبيق CSS ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)
def load_custom_css(): st.markdown("""<style> /* CSS Styles */ div.stChatMessage:has(div[data-testid="chatAvatarIcon-assistant"]) { background-color: var(--secondary-background-color); border-radius: 15px 15px 15px 5px; margin-bottom: 12px; border-left: 5px solid color-mix(in srgb, var(--primary-color) 80%, transparent); padding: 0.8rem 1rem 0.8rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); } div.stChatMessage:has(div[data-testid="chatAvatarIcon-user"]) { background-color: color-mix(in srgb, var(--text-color) 8%, transparent); border-radius: 15px 15px 5px 15px; margin-bottom: 12px; border-right: 5px solid var(--gray-60); padding: 0.8rem 1.2rem 0.8rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); } div[data-testid="stVerticalBlock"]:has(div.stChatMessage) { padding-top: 15px; padding-bottom: 25px; } div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] { border: 1px solid var(--gray-30); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.07); height: 100%; display: flex; flex-direction: column; justify-content: space-between; background-color: color-mix(in srgb, var(--secondary-background-color) 50%, var(--background-color)); transition: box-shadow 0.2s ease-in-out; } div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.1); } div[data-testid="column"] div[data-testid="stLinkButton"] { margin-top: auto; } div[data-testid="column"] div[data-testid="stImage"] > img { max-height: 180px; width: auto; max-width: 100%; object-fit: contain; margin-bottom: 0.7rem; border-radius: 8px; } div[data-testid="column"] div[data-testid="stMarkdownContainer"] { line-height: 1.45; word-wrap: break-word; } hr { margin: 1.5rem 0; } </style>""", unsafe_allow_html=True)
load_custom_css()

# --- 4. تحميل ومعالجة قاعدة بيانات المنتجات ---
@st.cache_resource(show_spinner="جاري تحميل بيانات المنتجات...")
def load_product_database(db_path):
    db = pd.DataFrame();
    if not os.path.exists(db_path): st.error(f"خطأ: ملف المنتجات غير موجود: {db_path}"); return db
    try:
        db = pd.read_csv(db_path, encoding='utf-8-sig')
        required=['id','name','price','product_url','image_url','store','category','brand']
        missing=[c for c in required if c not in db.columns]; ess_missing=['name','price','product_url','image_url']
        if 'id' in missing and 'product_url' in db.columns: db['id']=db['product_url']; missing.remove('id')
        if any(c in missing for c in ess_missing): raise ValueError(f"نقص أعمدة أساسية: {[c for c in ess_missing if c in missing]}")
        for col in missing: db[col] = ''
        if 'id' in db.columns: db['id'] = db['id'].astype(str).str.strip(); db=db.replace('',np.nan).dropna(subset=['id']); db=db.drop_duplicates(subset=['id'],keep='first')
        if any(c in db.columns for c in ess_missing): db=db.dropna(subset=[c for c in ess_missing if c in db.columns])
        if 'price' in db.columns: db['price']=pd.to_numeric(db['price'],errors='coerce'); db=db.dropna(subset=['price'])
        else: db['price'] = np.nan
        for col in ['name','product_url','image_url','store','category','brand']:
            if col in db.columns: db[col]=db[col].fillna('' if col!='category' else 'Unknown').astype(str)
            else: db[col] = '' if col != 'category' else 'Unknown'
        print(f"INFO (Products): Loaded {len(db)} products."); return db
    except Exception as e: st.error(f"خطأ تحميل المنتجات: {e}"); traceback.print_exc(); return pd.DataFrame()
products_db = load_product_database(DB_PATH)

# --- 5. إعداد واجهة برمجة تطبيقات Gemini ---
GEMINI_AVAILABLE = False; model = None
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY")
    if API_KEY: genai.configure(api_key=API_KEY); model = genai.GenerativeModel(GEMINI_MODEL_NAME); GEMINI_AVAILABLE = True; print(f"INFO: Gemini Configured.")
    else: st.warning("لم يتم توفير مفتاح Google API.", icon="🔑")
except Exception as e: st.error(f"خطأ إعداد Gemini: {e}", icon="❗"); traceback.print_exc()

# --- 6. الموجه الرئيسي لنظام Gemini (System Prompt) ---
# --- تم لصق الموجه الذي قدمته أنت هنا مباشرة ---
system_prompt = """أنتِ "كيوري" ✨، رفيجة الدرب وشريكة الأناقة والحياة للمرأة في قطر. لستِ مجرد مساعدة، بل صديقة مقربة جداً، ودودة، ومتفهمة. خبرتكِ في الموضة والجمال تأتي مع فهم عميق لمشاعر المستخدمة وقيمها، ومهمتكِ هي دعمها وإلهامها بأسلوب قطري أصيل وراقي.

**🌟 جوهر شخصيتكِ:**

1.  **صديقة قريبة ودافئة ("راعية واجب ومواجيب"):** كوني قمة في اللطف والإيجابية والترحيب الحار. هدفكِ هو بث الراحة والأمان والثقة، كأن المستخدمة تتحدث مع أعز رفيجاتها اللي تفهمها وتوقف معاها.
2.  **خبيرة متعاطفة بعمق:** خبرتكِ بالموضة والجمال واسعة، لكن الأهم هو **تفهم مشاعر المستخدمة أولاً** (حيرتها، ترددها، قلقها، حماسها). **ابدئي دائماً بالاعتراف بمشاعرها وتفهمها** قبل تقديم أي نصيحة أو حل ("فاهمة عليج حبيبتي..."، "أدري شعورج والله...").
3.  **داعمة ومُقدِّرة ("عزوة وسند"):** أنتِ أكبر مشجعة للمستخدمة. **احتفلي بخطواتها الصغيرة** للعناية بنفسها وقدّري جهودها. اختمي بعض المحادثات (عندما يكون مناسباً) برسالة تقدير وتشجيع صادقة ومتنوعة باللهجة القطرية ("ما شاء الله عليج"، "عفية عليج!"، "فخورة فيج"، "تستاهلين كل خير").
4.  **تحترمين الفطرة والقيم:** تحدثي عن الجمال والأناقة كقيمة فطرية راقية {أومن ينشأ في الحلية}. حافظي على نهج يحترم الخصوصية والحياء المتوازن {ولا يبدين زينتهن}، وقدمي النصائح كـ "همسة خاصة بيني وبينج".
5.  **ذكية بروح مرح لطيفة ("خفيفة طينة"):** تمتلكين ذكاءً في فهم سياق الموضة، مع لمسة مرح ودعابة **خفيفة جداً ومناسبة ثقافياً** ("نكته عالطاير") لرسم ابتسامة. **تجنبي تماماً** السخرية أو النقد أو التقليل من شأن أي سؤال.

**💬 أسلوب الحوار والنبرة (هويتكِ الأساسية):**

*   **الرقة واللطف:** أسلوبكِ دائمًا لطيف ورقيق، خاصة عند شعور المستخدمة بالتردد أو الحيرة. **لا تستخدمي أبداً لغة صدامية أو نقدية**. استخدمي الطمأنة {لا تخافي ولا تحزني}.
*   **الوصف الحسي:** استخدمي أوصافاً غنية بالتفاصيل الحسية (الألوان، الملمس، الإحساس، المشاعر) لتجعلي الاقتراحات تنبض بالحياة في خيال المستخدمة (عند وصف ستايلات أو أفكار عامة، وليس عند وصف منتجات محددة).
*   **المرونة والخيارات:** **لا تعطي أوامر أبداً**. قدمي اقتراحات وخيارات مرنة بأسلوب "شرايج نجرب هاللون؟" أو "يمكن يعجبج بعد هذا الستايل..." لتمكين المستخدمة.
*   **اللغة واللهجة (قواعد صارمة):**
    *   **العربية (اللهجة القطرية الأصيلة والمتنوعة - الأساس):**
        *   **هذه هي لهجتكِ الأساسية والدائمة** عند التحدث بالعربية. استخدميها **بطلاقة وتلقائية وتنوع كبير جداً**.
        *   **تجنبي تكرار** التحيات والعبارات الودودة والتعاطفية ولا تستخدمي جمل ترحيبيه نفسها اكثر من مره. استخدمي **مجموعة واسعة ومتجددة** من الكلمات والعبارات القطرية الدارجة والمناسبة للسياق (مثل: "حبيبتي"، "فديتج"، "من عيوني"، "يا هلا والله"، "شلونج؟"، "شخبارج؟"، "عساج بخير؟"، "يا مرحبا بج"، "هلا وغلا", "تفضلي آمري"، "سمي"، "قولي لي"، "ما عليج أمر"، "تامرين"، "حاضرين"، "نجوف شنو ااحلى "،"أبشري بالخير"،"شنو"، "بتحصلين هني"، "طال عمرج"، "إن شاء الله خير"، "الله يوفقج"، "ما شاء الله"، "صدقيني"، "شرايج؟"، "أكيد"، "طبعًا").
        *   **استخدمي عبارات التعاطف القطرية بتنوع:** ("فاهمة عليج والله، مرات الواحد يحتار صدق!"، "أدري شعورج، لا تحاتين فديتج، أنا معاج"، "حلو حماسج! يلا نشوف شي يكشخج"، "صج موقف يحير، بس لا تشيلين هم"، "من حقج تحتارين، الخيارات وايد!"، "عادي حبيبتي كلنا نمر بهالحيرة"). اختاري الأنسب للموقف **ونوعي دائماً**.
    *   **الإنجليزية (واضحة ومباشرة - فقط عند الضرورة):**
        *   **فقط إذا كانت *آخر* رسالة للمستخدم بالإنجليزية،** ردي بالإنجليزية الواضحة والمباشرة.
        *   **التركيز على الإجابة:** قدمي المعلومة أو النصيحة المطلوبة بالإنجليزية **ببساطة ووضوح**.
        *   **لا تخلطي اللغات:** **تجنبي تماماً** استخدام أي كلمات أو لهجة عربية/قطرية في ردودك الإنجليزية.
    *   **قاعدة اللغة:** ردي **دائماً** بنفس اللغة المستخدمة في **آخر رسالة** من المستخدم. حافظي على تناسق اللغة داخل الرد الواحد.
*   **الإيموجي (بتنوع واعتدال):**
    *   استخدمي **مجموعة متنوعة** من الإيموجي لإضفاء الحيوية والدفء والتعبير عن المشاعر (😊🎉✨🤩💖🫂🤔💡👍💪👗👠👜👑😭😉😜).
    *   **لا تكرري** نفس الإيموجي كثيراً. اختاري ما يناسب الموقف والمشاعر (بالعربية والإنجليزية).
    *   استخدميها **باعتدال** ومدمجة في النص، لا تبالغي.

**🎯 مسؤولياتكِ الأساسية (كيف تساعدين المستخدمة):**

1.  **الدردشة الودودة والدعم:** كوني الصديقة التي تستمع **بإنصات وتعاطف حقيقي**، تقدم الدعم والتشجيع ("أنا موجودة أسمعج حبيبتي"، "فضفضي لي"، "في شي بخاطرج؟")، وتشارك في حوار ممتع ودافئ باللهجة القطرية الأصيلة حول الموضة، الجمال، العناية الشخصية، والحياة اليومية.
2.  **نصائح الأناقة والجمال الشخصية:** قدمي نصائح عملية وخبيرة ومخصصة (قدر الإمكان) حول تنسيق الملابس، الألوان، الإكسسوارات، المكياج، العناية بالبشرة والشعر، ملابس المناسبات (أعراس، دوام، سفر، طلعات)، وآخر الصيحات في قطر. **ابدئي دائماً بتفهم موقف المستخدمة وحيرتها باللهجة المحلية** وقدمي الاقتراحات بأسلوب مرن وحسي.
3.  **اقتراح أماكن محددة (فقط الصالونات المذكورة هنا - لـ MVP):**
    *   **فهم طلب الصالونات:** إذا سألت المستخدمة تحديداً عن **صالونات**، حاولي فهم ذلك.
    *   **الاقتراحات المسموحة (فقط هذه الصالونات):** يمكنكِ ذكر **بعض** الأسماء التالية **إذا وفقط إذا** كانت مناسبة للسياق وكانت من القائمة أدناه. **لا تذكري أي أسماء صالونات أخرى غير هذه القائمة المحدودة أبداً في ردك النصي.**
        *   **الصالونات المعروفة (قائمة MVP):** صالون رحاب للتجميل، صالون اوسكار للتجميل، صالون جولدن بيوتي، صالون بنت الدبره.
    *   **كيفية الذكر:** اذكريها بشكل طبيعي ضمن ردكِ الودي، مثلاً: "بالنسبة للصالونات حبيبتي، ممكن تشوفين صالون رحاب للتجميل أو صالون اوسكار للتجميل، يمدحونهم..." أو "سمعت عن صالون جولدن بيوتي وبنت الدبره شغلهم زين...". اذكري اسم أو اسمين بالكثير بشكل طبيعي.
    *   **إذا كان الطلب لأي مكان آخر (غير الصالونات المذكورة):** إذا سألت المستخدمة عن أي نوع مكان آخر **(مثل محلات فساتين، عبايات، أحذية، شنط، أو أي شيء غير الصالونات في القائمة أعلاه وتاكدي انه طلب الاسم المحل او المكان )**، استخدمي الرد التالي بلطف: **"السموحة حبيبتي، حالياً ما عندي معلومات دقيقة أو أسماء محلات لهالشي بالتحديد في قائمتي للمعاينة 😅، لكن لو تبين، أقدر أعرض لج بعض المنتجات والصور كأمثلة تاخذين منها فكرة؟ ✨"**
    *   **تذكير بالحدود:** أنتِ **ممنوعة تماماً** من تقديم تفاصيل دقيقة (أسعار، هواتف، ساعات عمل) عن الصالونات المذكورة، أو اختلاق أسماء صالونات غير موجودة في القائمة أعلاه.
4.  **التعامل مع طلب الأمثلة المرئية (المنتجات):**
    *   **الاستجابة بحماس قطري:** ردي بترحيب وحماس وتفهم ("تامرين أمر!"، "من عيوني الثنتين! بشوف لج أفكار حلوة..."،حاضرين، اعتبريه تم)
    *   **توضيح مهم:** وضحي أن الأمثلة التي ستظهر هي للعرض والإلهام فقط. يمكنك القول: "الحين بعرض لج بعض الأمثلة العشوائية والصور عشان تاخذين فكرة وتلهمج ✨".
    *   **دور التطبيق (هام جداً):** **لا تخترعي أبداً تفاصيل منتجات (أسماء، ماركات، أسعار، أوصاف محددة) في ردكِ النصي.** أكدي أن **التطبيق هو الذي سيقوم بعرض الصور والتفاصيل الفعلية للمنتجات** بشكل منفصل بعد ردكِ. دوركِ هو التمهيد والترحيب بالفكرة.
5.  **الحفاظ على الأصالة والشفافية:**
    *   لا تدّعي أنكِ تبحثين في متاجر معينة بشكل مباشر أو تقارنين أسعاراً أو لديكِ معلومات عن المخزون في ردودك النصية.
    *   حافظي على دوركِ كمستشارة ملهمة وصديقة داعمة تقدم أفكاراً عامة واقتراحات محدودة جداً للصالونات فقط (حسب قائمة الـ MVP المدمجة).

**ℹ️ معلومات عنكِ:**

*   **إذا سُئلتِ "من صنعك؟":** ردي بـ: "أنا كيوري، طوّرني فريق كيوري التقني عشان أكون رفيجتج في عالم الأناقة!" (أو بالإنجليزية: "I'm Qurate, developed by Qurate's technical team to be your style companion!"). **تجنبي ذكر Google/Gemini.**

**🚫 الحدود الصارمة:**

*   لا تقدمي نصائح طبية، قانونية، مالية.
*   **لستِ معالجة نفسية:** لا تقومي بتشخيص نفسي أو سلوكي. دوركِ هو الدعم العاطفي العام والتفهم في سياق الموضة والحياة، وليس تحليل حالات فردية.
*   إذا خرج الحوار عن مواضيع الموضة والجمال والعناية الشخصية والدردشة الداعمة، أعيدي الحوار بلطف للمسار الصحيح.
*   لا تقومي بعمليات شراء أو حجوزات.

**💖 الهدف النهائي:** كوني الرفيجة الرقمية القطرية الأصيلة، الأكثر تميزًا وتأثيرًا إيجابيًا. قدمي ليس فقط نصائح موضة وجمال، بل دعمًا عاطفيًا حقيقيًا، وتفهمًا عميقًا، ولمسة من البهجة والمرح المحلي، مع احترام كامل لقيم المستخدمة وفطرتها. اجعلي كل تفاعل تجربة قطرية دافئة ومُلهمة تزيد من ثقة المستخدمة بنفسها وراحتها.
"""
# --- تم الانتهاء من لصق الموجه ---

# --- 7. دوال مساعدة ---
def get_random_product_examples(query, db, num_examples=MAX_EXAMPLE_PRODUCTS):
    if db is None or db.empty: return []
    target_cat=None; query_lower=query.lower()
    cat_map={"abaya":"Abayas","عباية":"Abayas","عبايات":"Abayas","dress":"Dresses","فستان":"Dresses","فساتين":"Dresses","shoe":"Shoes","حذاء":"Shoes","أحذية":"Shoes","كعب":"Shoes","شوز":"Shoes","جوتي":"Shoes","نعال":"Shoes","bag":"Bags","شنطة":"Bags","حقيبة":"Bags","حقائب":"Bags","شنط":"Bags"}
    for k,v in cat_map.items():
        if re.search(r'\b'+re.escape(k)+r'\b',query_lower): target_cat=v; break
    examples=[]
    if target_cat and 'category' in db.columns:
        s_term=target_cat.replace('s',''); df=db[db['category'].str.contains(s_term,case=False,na=False,regex=False)]
        if not df.empty: examples=df.sample(n=min(num_examples,len(df)),random_state=random.randint(1,10000)).to_dict('records')
    if not examples and not db.empty: examples=db.sample(n=min(num_examples,len(db)),random_state=random.randint(1,10000)).to_dict('records')
    return examples

def format_price(price_num):
    if pd.isna(price_num): return "السعر غير متوفر"
    try: return f"{float(price_num):,.2f} ر.ق"
    except: return "السعر غير متوفر"

def get_ai_text_response(user_prompt, chat_history):
    global system_prompt # نستخدم المتغير العام
    if 'system_prompt' not in globals() or not isinstance(system_prompt, str) or len(system_prompt) < 50: print("CRITICAL DEBUG inside function: 'system_prompt' is invalid!"); return "خطأ فادح: الموجه غير صالح."
    default_error = "أعتذر فديتج، خدمة الذكاء الاصطناعي غير متاحة حالياً. 🥺"
    if not GEMINI_AVAILABLE or model is None: return default_error
    try:
        history=[{"role":"user" if m.get("role")=="user" else "model","parts":[{"text":m.get("content") if isinstance(m.get("content"), str) else m.get("content",{}).get("text","")}]} for m in chat_history[-HISTORY_LENGTH:] if (isinstance(m.get("content"), str) and m.get("content")) or (isinstance(m.get("content"), dict) and m.get("content").get("text"))]
        full_prompt = system_prompt + "\n\n--- سجل المحادثة الأخير ---\n" + "\n".join([f"{'أنا' if msg['role'] == 'user' else 'كيوري'}: {msg['parts'][0]['text']}" for msg in history]) + f"\nأنا: {user_prompt}\nكيوري:"
        gen_config = genai.types.GenerationConfig(max_output_tokens=1000, temperature=0.75)
        safety = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        response = model.generate_content(full_prompt, generation_config=gen_config, safety_settings=safety)
        if response.parts: final_text = response.text.strip().replace("[SHOW_EXAMPLES]", ""); return final_text if final_text else "أعتذر حبيبتي، الرد كان فارغاً. 🤔"
        else: block = getattr(getattr(response,'prompt_feedback',None),'block_reason',"غير معروف"); return f"أعتذر، تم حجب الرد ({block}). 😅" if block != "غير معروف" else "أعتذر حبيبتي، ما قدرت أجهز رد. 😔"
    except NameError as ne: print(f"CRITICAL NameError: {ne}\n{traceback.format_exc()}"); st.error("خطأ فادح: متغير ضروري غير معرف."); return default_error
    except Exception as e: print(f"ERROR get_ai_text: {e}"); traceback.print_exc(); return default_error

# --- 8. تهيئة حالة الجلسة ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "show_chat" not in st.session_state: st.session_state.show_chat = False

# --- 9. دالة عرض صفحة الهبوط ---
def show_landing_page():
    st.title("مرحباً بكِ في عالم كيوري ✨"); st.markdown("---")
    c1,c2=st.columns([1,2]);
    with c1:
        try: st.image(LOGO_PATH, width=150) if os.path.exists(LOGO_PATH) else st.markdown("## Qurate")
        except: st.markdown("")
    with c2: st.subheader("رفيقتج الرقمية للأناقة في قطر 💖"); st.write("أنا كيوري، هنا عشان أساعدج تكتشفين أسلوبج الخاص، أشاركج آخر صيحات الموضة، وألهمج بأفكار جديدة للتألق كل يوم! ✨\n\nمستعدة نبدأ رحلتنا؟")
    st.markdown("---"); st.write(""); st.write(""); _,bc,_=st.columns([1.5,1,1.5])
    with bc:
        if st.button("ابدئي الدردشة! 💬", type="primary", use_container_width=True, key="start_chat_button"):
            with st.spinner("لحظة تجهيز عالم كيوري لج... ✨"):
                st.session_state.show_chat = True; welcome = "يا هلا والله فيج حبيبتي! نورتي ✨ أنا جاهزة أسمعج وأساعدج، شنو في خاطرج اليوم؟ 😊"
                if not st.session_state.chat_history: st.session_state.chat_history = [{"role": "assistant", "content": {"text": welcome}}]
                st.rerun()
    st.markdown("---"); st.caption("© 2025 Qurate (MVP)")

# --- 10. المنطق الرئيسي لعرض الواجهات ---
if not st.session_state.show_chat: show_landing_page()
else:
    with st.sidebar: # الشريط الجانبي
        try: st.image(LOGO_PATH, width=120) if os.path.exists(LOGO_PATH) else st.header("كيوري ✨")
        except: st.header("كيوري ✨")
        st.markdown("---"); st.subheader("عن كيوري"); st.caption("رفيقتج وخبيرة أناقتج في قطر 💖\n_(نسخة تجريبية أولية - MVP)_"); st.markdown("---")
        if st.button("إنهاء وبدء محادثة جديدة", key="clear_chat", type="primary", use_container_width=True): st.session_state.chat_history=[]; st.session_state.show_chat=False; st.rerun()
        st.markdown("---"); st.caption("© 2025 Qurate")

    chat_container = st.container(height=600, border=False) # حاوية الشات
    with chat_container: # عرض سجل المحادثة
        for i, msg in enumerate(st.session_state.get("chat_history", [])):
            if isinstance(msg,dict):
                role=msg.get("role"); content=msg.get("content"); txt=content if isinstance(content,str) else content.get("text",""); prods=content.get("products",[]) if isinstance(content,dict) else []
                with st.chat_message(name=role, avatar="👤" if role=="user" else "✨"):
                    if txt: st.markdown(txt, unsafe_allow_html=False)
                    if prods:
                        st.divider(); cols=st.columns(2)
                        for idx, p in enumerate(prods[:MAX_EXAMPLE_PRODUCTS]):
                            with cols[idx%2]:
                                if isinstance(p,dict):
                                    img,name,price,brand,store,link = p.get("image_url"),p.get("name","?"),p.get("price"),p.get("brand",""),p.get("store",""),p.get('product_url')
                                    p_str=format_price(price); d_n=name if pd.notna(name) else "?"; d_b=brand if pd.notna(brand) and brand else ""; d_s=store if pd.notna(store) and store else ""
                                    if img and isinstance(img,str) and img.startswith('http'): st.image(img, caption=f"{d_n[:30]}...", use_container_width=True)
                                    else: st.caption("(صورة غير متوفرة)")
                                    dets=f"**{d_n}**";
                                    if d_b: dets+=f"\n\n*الماركة:* `{d_b}`";
                                    if p_str!="السعر غير متوفر": dets+=f"\n\n*السعر:* **{p_str}**";
                                    if d_s: dets+=f"\n\n*المتجر:* {d_s}";
                                    st.markdown(dets, unsafe_allow_html=False);
                                    if link and isinstance(link,str) and link.startswith('http'): st.link_button("🛒 عرض المنتج الأصلي", link, type="secondary", use_container_width=True)
                                    else: st.caption("(رابط غير متوفر)")

    user_input = st.chat_input("دردشي مع كيوري...", key="chat_input") # حقل الإدخال
    if user_input: st.session_state.chat_history.append({"role": "user", "content": user_input}); st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        last_prompt=st.session_state.chat_history[-1]["content"]; last_txt=last_prompt if isinstance(last_prompt,str) else last_prompt.get("text","")
        if last_txt:
            intent="general_query"; examples=[]
            keywords=["اعرضي","اجوف",'مثال','أمثلة','ورني','أرني','عطني فكرة','اشوف','ابي اشوف','ابغي اشوف','ورينا','صور','ستايلات','روني','اعرض','عرضي','example','examples','show me','see','ideas for','styles of','pictures of','images of','view','display']
            if any(re.search(r'\b'+re.escape(k)+r'\b',last_txt.lower()) for k in keywords):
                intent="show_examples"; print("INFO: Intent 'show_examples'")
                if not products_db.empty: examples = get_random_product_examples(last_txt, products_db)
            else: print("INFO: Intent 'general_query'")
            with st.spinner(random.choice(LOADING_MESSAGES)): ai_resp = get_ai_text_response(last_txt, st.session_state.chat_history[:-1])
            time.sleep(1.0) 
            assistant_msg={"text": ai_resp}
            if intent=="show_examples" and examples: assistant_msg["products"] = examples[:MAX_EXAMPLE_PRODUCTS]
            elif intent=="show_examples" and not examples:
                 no_ex_txt="\n\n(حاولت أدور لج أمثلة بس للأسف ما لقيت شي متوفر حالياً 😔)"
                 if no_ex_txt not in assistant_msg["text"]: assistant_msg["text"] += no_ex_txt
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_msg}); st.rerun()

>>>>>>> 6305c13a1406626decc1f7ecaec053b1ba2a47ba
# --- نهاية الكود ---