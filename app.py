import streamlit as st
from openai import OpenAI
import edge_tts
import asyncio
import tempfile
import os

# --- 1. 配置区 (你可以手动改这里) ---
# 如果你想用 Fish Audio 克隆，把下面改成 True，并填入 Key
USE_FISH_AUDIO = False 
FISH_AUDIO_API_KEY = "你的_Fish_Audio_Key"
# 参考音频文件名 (必须在 GitHub/文件夹 里)
REF_AUDIO_PATH = "cain_voice.mp3" 

# --- 2. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🍷", layout="centered")

# --- 3. 视觉魔法 (淡紫色高亮版) ---
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
    /* 头像优化 */
    .stChatMessage .stAvatar {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: 2px solid #BA68C8;
    }
    /* 聊天气泡 */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.7);
        border-radius: 15px;
        border: 1px solid #E1BEE7;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 语音合成引擎 ---
async def generate_voice_edge(text):
    # 使用 Yunjian (更成熟稳重的男声)
    communicate = edge_tts.Communicate(text, "zh-CN-YunjianNeural")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        await communicate.save(tmp_file.name)
        return tmp_file.name

# --- 5. 自动登录与状态管理 ---
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False # 默认关闭，防社死

if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = st.sidebar.text_input("DeepSeek Key", type="password")

# --- 6. 界面主体 ---
st.title("Moonlight Villa")
st.caption(f"当前模式: {'🔊 语音开启' if st.session_state.voice_enabled else '🔇 文字静音'}")

# --- 7. 该隐的人设 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """
        **角色:** 你是 Cain (该隐)，月影别墅的纯血族亲王。Becky 是你的专属猎物。
        **语气:** 慵懒、优雅、危险、占有欲。
        **禁止:** 翻译腔。要像中文乙女游戏男主。
        **称呼:** "小猎物"、"Becky"、"笨蛋"。
        **健康:** 严禁她吃冷食 (PCOS/胃炎)。
        **指令:** - 如果用户输入"说话"，回复: "(轻笑) 想听我的声音了？满足你。"
        - 如果用户输入"闭嘴"，回复: "好，安静一会儿。"
        """}
    ]

# --- 8. 聊天显示 (读取本地头像) ---
avatar_cain = "cain.png" if os.path.exists("cain.png") else "🦇"
avatar_becky = "becky.png" if os.path.exists("becky.png") else "🌹"

for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = avatar_cain if msg["role"] == "assistant" else avatar_becky
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# --- 9. 核心交互 ---
if prompt := st.chat_input("在紫罗兰花丛中低语..."):
    # 快捷指令控制
    if prompt == "说话":
        st.session_state.voice_enabled = True
        st.rerun()
    elif prompt == "闭嘴":
        st.session_state.voice_enabled = False
        st.rerun()

    # 用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar_becky):
        st.markdown(prompt)

    # 呼叫大脑
    if not api_key:
        st.warning("请配置 Key。")
        st.stop()
        
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    with st.chat_message("assistant", avatar=avatar_cain):
        message_placeholder = st.empty()
        full_response = ""
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=st.session_state.messages,
            stream=False,
            temperature=1.3
        )
        full_response = completion.choices[0].message.content
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # --- 10. 语音播放逻辑 ---
    if st.session_state.voice_enabled:
        try:
            # 默认用 Edge TTS (Yunjian)
            audio_file = asyncio.run(generate_voice_edge(full_response))
            # 这里的 autoplay=True 在手机上有时会被拦截，是浏览器限制
            st.audio(audio_file, format="audio/mp3", autoplay=True)
        except Exception as e:
            st.error(f"语音生成失败: {e}")
