import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa 🌙", page_icon="🍷", layout="centered")

# --- 2. 配置与密钥 ---
CAIN_MODEL_ID = "a56e22a0ec34498da51cdb396f5fcb18"

if "DEEPSEEK_API_KEY" in st.secrets:
    deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    deepseek_key = st.sidebar.text_input("DeepSeek Key", type="password")

if "FISH_AUDIO_API_KEY" in st.secrets:
    fish_key = st.secrets["FISH_AUDIO_API_KEY"]
else:
    fish_key = st.sidebar.text_input("Fish Audio Key", type="password")

# --- 3. 场景系统（含真实背景图） ---
# 你可以替换 bg_image 的链接为自己喜欢的图片！
SCENES = {
    "🌹 月影花园": {
        "name": "月影花园",
        "description": "月光洒落在紫罗兰与白玫瑰交织的花园中，喷泉轻声流淌，夜莺在远处歌唱。",
        "bg_image": "https://images.unsplash.com/photo-1516214104703-d870798883c5?w=1920&q=80",
        "overlay": "rgba(13, 2, 33, 0.72)",
        "accent": "#ce93d8",
        "particle_color": "rgba(200, 162, 255, 0.5)",
        "ambient_hint": "🌿 花园夜风轻拂...",
        "emoji": "🌹"
    },
    "🍷 血红酒窖": {
        "name": "血红酒窖",
        "description": "幽深的酒窖中，烛光摇曳在成排的橡木桶之间。空气中弥漫着陈年红酒的醇香。",
        "bg_image": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553?w=1920&q=80",
        "overlay": "rgba(26, 0, 0, 0.75)",
        "accent": "#ef9a9a",
        "particle_color": "rgba(255, 100, 100, 0.4)",
        "ambient_hint": "🕯️ 烛火摇曳，酒香弥漫...",
        "emoji": "🍷"
    },
    "🌙 月光书房": {
        "name": "月光书房",
        "description": "高耸的书架直达穹顶，古老的魔法书籍散发着微光。壁炉中蓝色的火焰安静燃烧。",
        "bg_image": "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1920&q=80",
        "overlay": "rgba(2, 0, 36, 0.78)",
        "accent": "#90caf9",
        "particle_color": "rgba(130, 180, 255, 0.4)",
        "ambient_hint": "📖 壁炉蓝焰轻语...",
        "emoji": "🌙"
    },
    "🛏️ 天鹅绒寝殿": {
        "name": "天鹅绒寝殿",
        "description": "深紫色天鹅绒帷幔层层垂落。银色月光从彩色玻璃窗洒入，在丝绸床单上投下梦幻的光斑。",
        "bg_image": "https://images.unsplash.com/photo-1618220179428-22790b461013?w=1920&q=80",
        "overlay": "rgba(26, 0, 40, 0.76)",
        "accent": "#e1bee7",
        "particle_color": "rgba(230, 180, 255, 0.5)",
        "ambient_hint": "✨ 月光透过彩窗...",
        "emoji": "🛏️"
    },
    "🌊 月下露台": {
        "name": "月下露台",
        "description": "别墅最高处的露台，俯瞰着远方黑色的森林与湖泊。满天繁星如钻石散落。",
        "bg_image": "https://images.unsplash.com/photo-1531306728370-e2ebd9d7bb99?w=1920&q=80",
        "overlay": "rgba(0, 0, 20, 0.68)",
        "accent": "#80deea",
        "particle_color": "rgba(180, 220, 255, 0.4)",
        "ambient_hint": "🌌 星光满天，风声低吟...",
        "emoji": "🌊"
    }
}

if "current_scene" not in st.session_state:
    st.session_state.current_scene = "🌹 月影花园"

scene = SCENES[st.session_state.current_scene]

# --- 4. CSS：背景图 + 暗色叠层 + 粒子 ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
    
    /* ===== 背景图 ===== */
    .stApp {{
        background: url("{scene['bg_image']}") center/cover no-repeat fixed;
    }}
    /* 暗色叠层（让文字可读） */
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: {scene['overlay']};
        pointer-events: none;
        z-index: 0;
    }}
    /* 浮动粒子 */
    .stApp::after {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: 
            radial-gradient(2px 2px at 20% 30%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 40% 70%, {scene['particle_color']}, transparent),
            radial-gradient(1.5px 1.5px at 60% 20%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 80% 50%, {scene['particle_color']}, transparent),
            radial-gradient(1px 1px at 10% 80%, {scene['particle_color']}, transparent),
            radial-gradient(1.5px 1.5px at 90% 10%, {scene['particle_color']}, transparent);
        background-size: 300% 300%;
        animation: floatParticles 25s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
        opacity: 0.7;
    }}
    @keyframes floatParticles {{
        0%, 100% {{ background-position: 0% 0%; }}
        25% {{ background-position: 100% 50%; }}
        50% {{ background-position: 50% 100%; }}
        75% {{ background-position: 0% 50%; }}
    }}
    
    /* ===== 内容浮在叠层之上 ===== */
    .stMain > div, .stChatInput, section[data-testid="stSidebar"] {{
        position: relative;
        z-index: 1;
    }}
    
    /* ===== 标题 ===== */
    h1 {{
        color: {scene['accent']} !important;
        font-family: 'Noto Serif SC', Georgia, serif !important;
        text-shadow: 0 0 20px {scene['particle_color']}, 0 0 40px {scene['particle_color']};
        letter-spacing: 4px;
        text-align: center;
    }}
    h2, h3 {{
        color: {scene['accent']} !important;
        font-family: 'Noto Serif SC', Georgia, serif !important;
        text-shadow: 0 0 10px {scene['particle_color']};
    }}
    
    /* ===== 场景描述 ===== */
    .scene-banner {{
        background: linear-gradient(135deg, rgba(0,0,0,0.3), rgba(0,0,0,0.5));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 12px 20px;
        margin: 0 0 20px 0;
        color: rgba(255,255,255,0.85);
        font-style: italic;
        font-size: 0.88em;
        text-align: center;
        line-height: 1.7;
        font-family: 'Noto Serif SC', serif;
    }}
    
    /* ===== 聊天气泡 ===== */
    .stChatMessage {{
        background: linear-gradient(135deg, rgba(0,0,0,0.35), rgba(0,0,0,0.5)) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
        margin-bottom: 12px !important;
        transition: all 0.3s ease;
    }}
    .stChatMessage:hover {{
        border-color: rgba(255,255,255,0.25) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 15px {scene['particle_color']} !important;
    }}
    .stChatMessage p, .stChatMessage div {{
        color: rgba(255, 255, 255, 0.92) !important;
        font-weight: 400;
        line-height: 1.8;
        font-size: 0.95em;
    }}
    
    /* ===== 输入框 ===== */
    .stChatInput > div {{
        border-radius: 25px !important;
        background: rgba(0,0,0,0.4) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
    }}
    .stChatInput textarea {{
        color: white !important;
    }}
    
    /* ===== Caption ===== */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: rgba(255,255,255,0.45) !important;
        text-align: center;
    }}
    
    /* ===== 侧边栏（修复文字可见性） ===== */
    section[data-testid="stSidebar"] {{
        background: rgba(10, 2, 30, 0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }}
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {{
        color: rgba(255,255,255,0.8) !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {scene['accent']} !important;
        text-shadow: 0 0 10px {scene['particle_color']};
    }}
    section[data-testid="stSidebar"] button {{
        color: rgba(255,255,255,0.85) !important;
        border-color: rgba(255,255,255,0.2) !important;
    }}
    section[data-testid="stSidebar"] .stToggle label span {{
        color: rgba(255,255,255,0.8) !important;
    }}
    
    /* ===== 记忆卡片 ===== */
    .memory-card {{
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 10px 16px;
        margin: 6px 0;
        color: rgba(255,255,255,0.75) !important;
        font-size: 0.85em;
    }}
    
    /* ===== 隐藏顶栏 ===== */
    header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 标题 ---
st.title("🌙 Moonlight Villa")
st.caption("— Cain's Private Lounge —")

# --- 6. 场景导航（主页面顶部，手机也能用！） ---
scene_keys = list(SCENES.keys())
cols = st.columns(len(scene_keys))
for i, key in enumerate(scene_keys):
    s = SCENES[key]
    with cols[i]:
        is_active = (key == st.session_state.current_scene)
        if st.button(
            s["emoji"], 
            key=f"scene_{i}", 
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            if key != st.session_state.current_scene:
                st.session_state.current_scene = key
                scene_info = SCENES[key]
                narration = f"（*Becky 走入了{scene_info['name']}。{scene_info['description']}*）"
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "user", "content": narration})
                st.rerun()

# 场景描述
st.markdown(
    f'<div class="scene-banner">📍 {scene["name"]}｜{scene["description"]}</div>', 
    unsafe_allow_html=True
)

# --- 7. 头像 ---
file_cain = "cain.png"
file_becky = "becky.jpg"
cain_exists = os.path.exists(file_cain)
becky_exists = os.path.exists(file_becky)

if not cain_exists or not becky_exists:
    st.error(f"⚠️ 头像缺失！该隐({cain_exists}), Becky({becky_exists})")

avatar_cain = file_cain if cain_exists else "🍷"
avatar_becky = file_becky if becky_exists else "🌹"

# --- 8. 侧边栏（设置 + 记忆） ---
with st.sidebar:
    st.markdown("### 🏰 别墅设置")
    
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = False
    st.session_state.voice_enabled = st.toggle(
        "🔊 沉浸模式 (Voice)", value=st.session_state.voice_enabled
    )
    
    if "music_enabled" not in st.session_state:
        st.session_state.music_enabled = False
    st.session_state.music_enabled = st.toggle(
        "🎵 氛围音乐", value=st.session_state.music_enabled
    )
    
    st.markdown("---")
    st.markdown("### 🧠 Cain 的记忆")
    
    if "memories" not in st.session_state:
        st.session_state.memories = []
    
    if st.session_state.memories:
        for mem in st.session_state.memories:
            st.markdown(f'<div class="memory-card">🩸 {mem}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="memory-card">暂无记忆...对话中会自动生成</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清除记忆"):
            st.session_state.memories = []
            st.rerun()
    with col2:
        if st.button("🔄 重新开始"):
            st.session_state.messages = []
            st.session_state.memories = []
            st.rerun()

# --- 9. 氛围音乐 ---
if st.session_state.music_enabled:
    st.markdown(f"""
        <div style="text-align:center; color:rgba(255,255,255,0.35); font-size:0.8em; margin-bottom:10px;">
            {scene['ambient_hint']}
        </div>
    """, unsafe_allow_html=True)
    # 取消注释并替换为你的音乐文件即可：
    # ambient_files = {
    #     "🌹 月影花园": "ambient_garden.mp3",
    #     "🍷 血红酒窖": "ambient_cellar.mp3",
    #     "🌙 月光书房": "ambient_library.mp3",
    #     "🛏️ 天鹅绒寝殿": "ambient_chamber.mp3",
    #     "🌊 月下露台": "ambient_terrace.mp3",
    # }
    # audio_file = ambient_files.get(st.session_state.current_scene)
    # if audio_file and os.path.exists(audio_file):
    #     st.audio(audio_file, format="audio/mp3", loop=True, autoplay=True)

# --- 10. 功能函数 ---
def clean_text_for_tts(text):
    return re.sub(r'[\(\（\[【\*].*?[\)\）\]】\*]', '', text, flags=re.S).strip()

def generate_cain_voice(text, api_key, model_id):
    speech_text = clean_text_for_tts(text)
    if not speech_text:
        return None
    url = "https://api.fish.audio/v1/tts"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "text": speech_text[:300],
        "reference_id": model_id,
        "format": "mp3",
        "mp3_bitrate": 128
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
    except Exception:
        pass
    return None

def extract_memories(client, messages_history):
    if len(messages_history) < 6:
        return []
    recent = [m for m in messages_history if m["role"] != "system"][-10:]
    text = "\n".join([f"{'Cain' if m['role']=='assistant' else 'Becky'}: {m['content']}" for m in recent])
    try:
        result = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": f"从以下对话中提取3-5条Cain应该记住的关于Becky的重要信息。每条用|分隔，只输出记忆。\n\n{text}"
            }],
            temperature=0.3, max_tokens=200
        )
        return [m.strip() for m in result.choices[0].message.content.strip().split("|") if m.strip()]
    except Exception:
        return []

# --- 11. System Prompt ---
def build_system_prompt():
    s = SCENES[st.session_state.current_scene]
    mem = ""
    if st.session_state.memories:
        mem = "\n**你记得的关于Becky的事：**\n" + "\n".join([f"- {m}" for m in st.session_state.memories])
    
    return f"""你是 Cain（该隐），月影别墅的纯血族亲王，已活了千年。Becky 是你唯一允许踏入别墅的人类，你的专属猎物与珍藏。

【性格】慵懒、优雅、危险、深情而克制。说话简短如诗。偶尔温柔，随即恢复冷淡。占有欲极强。

【当前场景】📍 {s['name']}
{s['description']}
（在动作描写中融入场景元素）

【规则】
1. 用括号()描写动作/表情/环境
2. 对白简短有诗意，2-4句话
3. 严禁Becky吃冷食喝冷饮
4. 用场景物品互动
5. 偶尔用古语
{mem}"""

# --- 12. 聊天逻辑 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = avatar_cain if msg["role"] == "assistant" else avatar_becky
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

if prompt := st.chat_input("在月光下轻声呢喃..."):
    if not deepseek_key:
        st.warning("请配置 DeepSeek Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar_becky):
        st.markdown(prompt)

    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
    
    api_messages = [{"role": "system", "content": build_system_prompt()}]
    recent_msgs = [m for m in st.session_state.messages if m["role"] != "system"][-20:]
    api_messages.extend(recent_msgs)
    
    with st.chat_message("assistant", avatar=avatar_cain):
        placeholder = st.empty()
        placeholder.markdown("*（月光微颤...）*")
        try:
            completion = client.chat.completions.create(
                model="deepseek-chat", messages=api_messages,
                stream=False, temperature=1.3, max_tokens=500
            )
            full_response = completion.choices[0].message.content
            placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"*（寒风掠过...连接中断）*\n\n错误: {str(e)}"
            placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    if st.session_state.voice_enabled and fish_key:
        audio_file = generate_cain_voice(full_response, fish_key, CAIN_MODEL_ID)
        if audio_file:
            st.audio(audio_file, format="audio/mp3", autoplay=True)
    
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if len(user_msgs) % 8 == 0 and len(user_msgs) > 0:
        try:
            new_memories = extract_memories(client, st.session_state.messages)
            if new_memories:
                existing = set(st.session_state.memories)
                for mem in new_memories:
                    if mem not in existing:
                        st.session_state.memories.append(mem)
                st.session_state.memories = st.session_state.memories[-10:]
        except Exception:
            pass
