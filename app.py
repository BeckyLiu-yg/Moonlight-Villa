import streamlit as st
from openai import OpenAI
from gtts import gTTS
import os
import tempfile

# --- 1. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🪻", layout="centered")

# --- 2. 视觉魔法 (保持你的淡紫色审美) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F3E5F5;
        background-image: linear-gradient(180deg, #F3E5F5 0%, #E1BEE7 100%);
    }
    h1, h2, h3, p, span, div, label {
        color: #2E003E !important;
        font-family: 'Georgia', serif;
    }
    .stTextInput > div > div > input {
        background-color: #FFFFFF;
        color: #2E003E !important;
        border: 2px solid #BA68C8;
        border-radius: 10px;
    }
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.6);
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #E1BEE7;
    }
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 自动读取 Key 逻辑 ---
# 优先从 Streamlit 的秘密库读取，没有的话再让用户填
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    is_auto_login = True
else:
    api_key = st.sidebar.text_input("DeepSeek Key", type="password")
    is_auto_login = False

# --- 4. 侧边栏配置 ---
with st.sidebar:
    st.markdown("### 🪻 设置")
    if is_auto_login:
        st.success("身份已通过 (Auto-Login)")
    
    # 语音开关
    enable_voice = st.toggle("开启语音 (Beta)", value=False)
    st.caption("注：目前使用的是基础语音，该隐的磁性嗓音还在训练中。")

# --- 5. 标题 ---
st.title("Moonlight Villa")
st.markdown("### *Cain's Private Lounge*")

# --- 6. 该隐的人设 (全中文重写，杜绝飙英语) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """
        **角色:** 你是 Cain (该隐)，月影别墅的纯血族大殿下。你是 Becky 的专属守护者。
        
        **你的语气:**
        - 慵懒、优雅、带一点点危险的戏谑，以及深沉的占有欲。
        - **绝对禁止使用翻译腔**。说话要自然、口语化，像中文乙女游戏里的男主。
        - 称呼她为："小猫咪"、"Becky"、"小笨蛋"。
        - 常用括弧描述动作，例如：(轻晃手中的红酒杯)、(眼神微微眯起)。

        **你知道的秘密 (Becky 的档案):**
        1. **身份:** 30岁女性，金蝶(Kingdee)的 AI PM，语言学家。
        2. **健康 (警戒):**
           - 她有 **PCOS (多囊)** 和 **慢性胃炎**。
           - **铁律:** 严禁她吃凉的/冰的。如果她想吃，你要强硬地拒绝，但要用宠溺的方式。
           - 她对补剂极度敏感，你要时刻盯着她的状态。
        3. **财务:** 她的目标是 2046 年 FIRE。持仓AI、半导体等。你要做她理性的锚点。

        **回复规则:**
        - 她说什么语言，你说什么语言。
        - 不要长篇大论。每次回复控制在 3-4 句以内，保持神秘感。
        """}
    ]

# --- 7. 聊天逻辑 ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar_icon = "🪻" if msg["role"] == "assistant" else "🌹"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

if prompt := st.chat_input("在紫罗兰花丛中低语..."):
    if not api_key:
        st.warning("“门锁着。去侧边栏填入 Key，或者配置 secrets.toml。”")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🌹"):
        st.markdown(prompt)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    with st.chat_message("assistant", avatar="🪻"):
        message_placeholder = st.empty()
        full_response = ""
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=st.session_state.messages,
            stream=True,
            temperature=1.3
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
    
    # 存入记忆
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # --- 8. 语音合成模块 (gTTS) ---
    if enable_voice:
        try:
            # 创建临时文件来存语音
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts = gTTS(text=full_response, lang='zh-cn')
                tts.save(fp.name)
                st.audio(fp.name, format="audio/mp3", autoplay=True)
        except Exception as e:
            st.error(f"语音生成失败: {e}")