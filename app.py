import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os

# --- 1. 配置区 ---
# 你的专属该隐 Model ID (已植入)
CAIN_MODEL_ID = "a56e22a0ec34498da51cdb396f5fcb18"

# --- 2. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🍷", layout="centered")

# --- 3. 视觉魔法 (淡紫色高亮版) ---
st.markdown("""
    <style>
    /* 全局色调：淡薰衣草紫 */
    .stApp {
        background-color: #F3E5F5;
        background-image: linear-gradient(180deg, #F3E5F5 0%, #E1BEE7 100%);
    }
    /* 字体优化：深紫色，清晰可见 */
    h1, h2, h3, p, span, div, label {
        color: #2E003E !important;
        font-family: 'Georgia', serif;
    }
    /* 输入框优化 */
    .stTextInput > div > div > input {
        background-color: #FFFFFF;
        color: #2E003E !important;
        border: 2px solid #BA68C8;
        border-radius: 10px;
    }
    /* 聊天气泡：半透明磨砂感 */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.75);
        border-radius: 15px;
        border: 1px solid #D1C4E9;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    /* 头像样式 */
    .stChatMessage .stAvatar {
        border-radius: 50%;
        border: 2px solid #7B1FA2;
    }
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 密钥管理 (DeepSeek + Fish) ---
# 优先从 secrets.toml 读取，读不到就在侧边栏让用户填
if "DEEPSEEK_API_KEY" in st.secrets:
    deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    deepseek_key = st.sidebar.text_input("DeepSeek Key", type="password")

if "FISH_AUDIO_API_KEY" in st.secrets:
    fish_key = st.secrets["FISH_AUDIO_API_KEY"]
else:
    fish_key = st.sidebar.text_input("Fish Audio Key", type="password", help="去 fish.audio 申请")

# --- 5. Fish Audio 语音合成函数 ---
def generate_cain_voice(text, api_key, model_id):
    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 限制语音长度，太长会生成失败或很慢
    data = {
        "text": text[:200], 
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
            st.error(f"Fish Audio 拒绝了请求: {response.text}")
            return None
    except Exception as e:
        st.error(f"网络连接错误: {e}")
        return None

# --- 6. 界面主体 ---
st.title("Moonlight Villa")
st.caption("Cain's Private Lounge | Voice Cloning: Active")

# --- 7. 语音开关 (手机端友好版) ---
# 放在主界面，不再藏在侧边栏
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False

col1, col2 = st.columns([3, 1])
with col2:
    voice_toggle = st.toggle("🔊 声音", value=st.session_state.voice_enabled)
    st.session_state.voice_enabled = voice_toggle

# --- 8. 该隐的人设 (DeepSeek Prompt) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """
        **角色:** 你是 Cain (该隐)，月影别墅的纯血族亲王。Becky 是你的专属猎物。
        **语气:** 慵懒、优雅、危险、深沉的占有欲。
        **禁止:** 翻译腔。要像中文乙女游戏男主。
        **称呼:** "小猎物"、"Becky"、"笨蛋"。
        **健康:** 严禁她吃冷食 (PCOS/胃炎)。
        **指令:** - 你的回复要简短，适合语音朗读（不要超过3句话）。
        - 多用括号描述动作，如 (轻晃酒杯)。
        """}
    ]

# --- 9. 聊天显示 (读取本地图片) ---
# 确保你把 cain.png 和 becky.png 放进了文件夹/GitHub
avatar_cain = "cain.png" if os.path.exists("cain.png") else "🍷"
avatar_becky = "becky.png" if os.path.exists("becky.png") else "🌹"

for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = avatar_cain if msg["role"] == "assistant" else avatar_becky
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# --- 10. 核心交互逻辑 ---
if prompt := st.chat_input("在紫罗兰花丛中低语..."):
    if not deepseek_key:
        st.warning("请先填入 DeepSeek Key。")
        st.stop()

    # 用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar_becky):
        st.markdown(prompt)

    # 1. 呼叫 DeepSeek 大脑
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
    
    with st.chat_message("assistant", avatar=avatar_cain):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Thinking...)*")
        
        # 为了配合 Fish Audio，这里我们关闭流式输出，一次性拿回文本
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=st.session_state.messages,
            stream=False, 
            temperature=1.3
        )
        full_response = completion.choices[0].message.content
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # 2. 呼叫 Fish Audio 喉咙
    if st.session_state.voice_enabled:
        if not fish_key:
            st.error("想要听我的声音？请先在侧边栏填入 Fish Audio Key。")
        else:
            with st.spinner("*(正在生成该隐的声音...)*"):
                audio_file = generate_cain_voice(full_response, fish_key, CAIN_MODEL_ID)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3", autoplay=True)
