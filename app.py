import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os
import re

# --- 1. 页面配置 (必须是第一行 Streamlit 命令) ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🍷", layout="centered")

# --- 2. 配置与密钥 ---
CAIN_MODEL_ID = "a56e22a0ec34498da51cdb396f5fcb18"

# 尝试从 secrets 读取，否则从侧边栏读取
if "DEEPSEEK_API_KEY" in st.secrets:
    deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    deepseek_key = st.sidebar.text_input("DeepSeek Key", type="password")

if "FISH_AUDIO_API_KEY" in st.secrets:
    fish_key = st.secrets["FISH_AUDIO_API_KEY"]
else:
    fish_key = st.sidebar.text_input("Fish Audio Key", type="password")

# --- 3. 视觉魔法 (回滚到最稳定的 V10 磨砂玻璃风) ---
st.markdown("""
    <style>
    /* 全局背景：深紫色 */
    .stApp {
        background: linear-gradient(135deg, #120024 0%, #320b54 50%, #4a148c 100%);
        background-attachment: fixed;
    }
    
    /* 标题：金色发光 */
    h1, h2, h3 {
        color: #E1BEE7 !important;
        font-family: 'Georgia', serif;
        text-shadow: 0 0 10px #7B1FA2;
    }

    /* 聊天气泡：高亮磨砂玻璃 */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.9); 
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }

    /* 文字颜色：强制深黑紫 */
    .stChatMessage p, .stChatMessage div {
        color: #1A0528 !important;
        font-weight: 500;
    }

    /* 隐藏顶部红条 */
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 标题区 (强制先渲染，防止界面消失) ---
st.title("Moonlight Villa")
st.caption("Cain's Private Lounge")

# --- 5. 头像诊断系统 (Avatar Check) ---
# 定义文件名
file_cain = "cain.png"
file_becky = "becky.png"

# 检查文件是否存在
cain_exists = os.path.exists(file_cain)
becky_exists = os.path.exists(file_becky)

# 如果找不到图片，显示红色的警告条 (只给 Becky 看)
if not cain_exists or not becky_exists:
    st.error(f"⚠️ 头像文件缺失！检测结果：该隐({cain_exists}), Becky({becky_exists})")
    st.info(f"当前云端目录下的文件有: {os.listdir('.')}")
    st.markdown("**请检查：** GitHub上的文件名是否大小写完全一致？(例如 cain.png 和 Cain.png 是不同的)")

# 设置头像变量
avatar_cain = file_cain if cain_exists else "🍷"
avatar_becky = file_becky if becky_exists else "🌹"

# --- 6. 语音开关 ---
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False

# 简单的开关 UI
voice_toggle = st.toggle("🔊 沉浸模式 (Voice)", value=st.session_state.voice_enabled)
st.session_state.voice_enabled = voice_toggle

# --- 7. 功能函数 ---
def clean_text_for_tts(text):
    # 清洗所有括号：() （） [] 【】
    return re.sub(r'[\(\（\[【].*?[\)\）\]】]', '', text, flags=re.S).strip()

def generate_cain_voice(text, api_key, model_id):
    speech_text = clean_text_for_tts(text)
    if not speech_text: return None # 如果全是动作描写，就不读

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "text": speech_text[:200], 
        "reference_id": model_id,
        "format": "mp3",
        "mp3_bitrate": 128
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
        else:
            return None
    except:
        return None

# --- 8. 聊天逻辑 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """
        **角色:** 你是 Cain (该隐)，月影别墅的纯血族亲王。Becky 是你的专属猎物。
        **语气:** 慵懒、优雅、危险、深沉。
        **指令:** 1. 必须使用括号描述动作。
        2. 严禁 Becky 吃冷食。
        3. 回复简短。
        """}
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = avatar_cain if msg["role"] == "assistant" else avatar_becky
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

if prompt := st.chat_input("在紫罗兰花丛中低语..."):
    if not deepseek_key:
        st.warning("请配置 DeepSeek Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar_becky):
        st.markdown(prompt)

    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
    
    with st.chat_message("assistant", avatar=avatar_cain):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Thinking...)*")
        
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=st.session_state.messages,
            stream=False, 
            temperature=1.4 
        )
        full_response = completion.choices[0].message.content
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    if st.session_state.voice_enabled and fish_key:
        with st.spinner("*(Listening...)*"):
            audio_file = generate_cain_voice(full_response, fish_key, CAIN_MODEL_ID)
            if audio_file:
                st.audio(audio_file, format="audio/mp3", autoplay=True)
