import streamlit as st
import datetime
import time

# إعداد الصفحة
st.set_page_config(
    page_title="🚧 تحت الصيانة 🚧",
    page_icon="🚧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# تصميم CSS مخصص
st.markdown("""
    <style>
    body {
        background-color: #f8f9fa;
    }
    .main {
        background-color: #f8f9fa;
        padding: 2rem;
    }
    .countdown-box {
        border-radius: 15px;
        padding: 20px;
        margin-top: 30px;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0,123,255,0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0,123,255,0); }
        100% { box-shadow: 0 0 0 0 rgba(0,123,255,0); }
    }
    .maintenance-icon {
        font-size: 5rem;
        text-align: center;
        margin-bottom: 10px;
    }
    .main-title {
        color: #dc3545;
        text-align: center;
        font-size: 2.8rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .description {
        text-align: center;
        color: #6c757d;
        font-size: 1.3rem;
        margin-bottom: 5px;
    }
    .thanks {
        text-align: center;
        font-size: 1.1rem;
        color: #6c757d;
    }
    </style>
""", unsafe_allow_html=True)

# تحديد وقت انتهاء الصيانة
maintenance_hours = 6  # ← عدد الساعات التي تريدها
end_time = datetime.datetime.now() + datetime.timedelta(hours=maintenance_hours)

# عرض الأيقونة
st.markdown("<div class='maintenance-icon'>🚧</div>", unsafe_allow_html=True)

# عرض العنوان
st.markdown("<div class='main-title'>التطبيق تحت الصيانة</div>", unsafe_allow_html=True)

# عرض الوصف
st.markdown("<div class='description'>نقوم ببعض التحديثات لتحسين تجربتك معنا</div>", unsafe_allow_html=True)

# عرض الشكر
st.markdown("<div class='thanks'>شكرًا لصبرك وتفهمك 🙏</div>", unsafe_allow_html=True)

# صندوق العداد
countdown_placeholder = st.empty()

# بدء عرض العداد
while True:
    now = datetime.datetime.now()
    remaining = end_time - now

    if remaining.total_seconds() <= 0:
        break

    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # تحديد اللون حسب الوقت المتبقي
    if remaining.total_seconds() > 3600:
        bg_color = "#28a745"  # أخضر (تبقى أكثر من ساعة)
    elif remaining.total_seconds() > 600:
        bg_color = "#fd7e14"  # برتقالي (تبقى أقل من ساعة)
    else:
        bg_color = "#dc3545"  # أحمر (تبقى أقل من 10 دقائق)

    countdown_text = f"""<div class='countdown-box' style='background-color: {bg_color}; color: white;'>
    ⏳ {hours:02d}:{minutes:02d}:{seconds:02d}
    </div>"""

    countdown_placeholder.markdown(countdown_text, unsafe_allow_html=True)
    time.sleep(1)

# (بدون ظهور أي رسالة إضافية بعد انتهاء الصيانة)
