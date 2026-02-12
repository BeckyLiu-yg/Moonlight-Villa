import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os
import re
import json

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

# --- 3. 场景系统 ---
SCENES = {
    "🌹 月影花园": {
        "name": "月影花园",
        "description": "月光洒落在紫罗兰与白玫瑰交织的花园中，喷泉轻声流淌，夜莺在远处歌唱。空气中弥漫着玫瑰与夜来香的芬芳。",
        "bg": "linear-gradient(135deg, #0d0221 0%, #1a0533 25%, #2d1b69 50%, #1a0533 75%, #150029 100%)",
        "particle_color": "rgba(200, 162, 255, 0.6)",
        "accent": "#ce93d8",
        "ambient_hint": "🌿 花园夜风轻拂..."
    },
    "🍷 血红酒窖": {
        "name": "血红酒窖",
        "description": "幽深的酒窖中，烛光摇曳在成排的橡木桶之间。空气中弥漫着陈年红酒的醇香，暗红色的丝绒帷幔垂落在石墙上。",
        "bg": "linear-gradient(135deg, #1a0000 0%, #330011 25%, #4a0020 50%, #2b0015 75%, #1a0000 100%)",
        "particle_color": "rgba(255, 100, 100, 0.5)",
        "accent": "#ef9a9a",
        "ambient_hint": "🕯️ 烛火摇曳，酒香弥漫..."
    },
    "🌙 月光书房": {
        "name": "月光书房",
        "description": "高耸的书架直达穹顶，古老的魔法书籍散发着微光。壁炉中蓝色的火焰安静燃烧，落地窗外是无尽的星空。",
        "bg": "linear-gradient(135deg, #020024 0%, #0a0a3e 25%, #0f1557 50%, #0a0a3e 75%, #020024 100%)",
        "particle_color": "rgba(130, 180, 255, 0.5)",
        "accent": "#90caf9",
        "ambient_hint": "📖 壁炉蓝焰轻语..."
    },
    "🛏️ 天鹅绒寝殿": {
        "name": "天鹅绒寝殿",
        "description": "奢华的寝殿中，深紫色天鹅绒帷幔层层垂落。银色月光从彩色玻璃窗洒入，在丝绸床单上投下梦幻的光斑。",
        "bg": "linear-gradient(135deg, #1a0028 0%, #2d0045 25%, #4a0072 50%, #2d0045 75%, #1a0028 100%)",
        "particle_color": "rgba(230, 180, 255, 0.6)",
        "accent": "#e1bee7",
        "ambient_hint": "✨ 月光透过彩窗..."
    },
    "🌊 月下露台": {
        "name": "月下露台",
        "description": "别墅最高处的露台，俯瞰着远方黑色的森林与湖泊。冷风带着松木与湖水的气息，满天繁星如钻石散落。",
        "bg": "linear-gradient(135deg, #000020 0%, #001030 25%, #0a2040 50%, #001030 75%, #000020 100%)",
        "particle_color": "rgba(180, 220, 255, 0.4)",
        "accent": "#80deea",
        "ambient_hint": "🌌 星光满天，风声低吟..."
    }
}

# 初始化场景
if "current_scene" not in st.session_state:
    st.session_state.current_scene = "🌹 月影花园"

scene = SCENES[st.session_state.current_scene]

# --- 4. 梦幻唯美 CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
    
    /* ===== 全局背景 ===== */
    .stApp {{
        background: {scene['bg']};
        background-attachment: fixed;
        font-family: 'Noto Serif SC', serif;
    }}
    
    /* ===== 浮动粒子动画 ===== */
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: 
            radial-gradient(2px 2px at 20% 30%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 40% 70%, {scene['particle_color']}, transparent),
            radial-gradient(1.5px 1.5px at 60% 20%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 80% 50%, {scene['particle_color']}, transparent),
            radial-gradient(1px 1px at 10% 80%, {scene['particle_color']}, transparent),
            radial-gradient(1.5px 1.5px at 90% 10%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 50% 90%, {scene['particle_color']}, transparent),
            radial-gradient(1px 1px at 70% 40%, {scene['particle_color']}, transparent),
            radial-gradient(1.5px 1.5px at 30% 60%, {scene['particle_color']}, transparent),
            radial-gradient(2px 2px at 85% 85%, {scene['particle_color']}, transparent);
        background-size: 300% 300%;
        animation: floatParticles 25s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
        opacity: 0.8;
    }}
    
    @keyframes floatParticles {{
        0%, 100% {{ background-position: 0% 0%; }}
        25% {{ background-position: 100% 50%; }}
        50% {{ background-position: 50% 100%; }}
        75% {{ background-position: 0% 50%; }}
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
    
    /* ===== 场景描述条 ===== */
    .scene-banner {{
        background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.1));
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 16px;
        padding: 12px 20px;
        margin: 0 0 20px 0;
        color: {scene['accent']};
        font-style: italic;
        font-size: 0.9em;
        text-align: center;
        line-height: 1.6;
    }}
    
    /* ===== 聊天气泡 ===== */
    .stChatMessage {{
        background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.15)) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1) !important;
        margin-bottom: 12px !important;
        transition: all 0.3s ease;
    }}
    .stChatMessage:hover {{
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.15), 0 0 15px {scene['particle_color']} !important;
    }}
    
    /* 文字颜色 */
    .stChatMessage p, .stChatMessage div {{
        color: rgba(255, 255, 255, 0.92) !important;
        font-weight: 400;
        line-height: 1.8;
        font-size: 0.95em;
    }}
    
    /* ===== 输入框美化 ===== */
    .stChatInput {{
        border-radius: 25px !important;
    }}
    .stChatInput > div {{
        border-radius: 25px !important;
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }}
    .stChatInput textarea {{
        color: white !important;
    }}
    
    /* ===== 侧边栏 ===== */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0d0221 0%, #1a0533 50%, #0d0221 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }}
    section[data-testid="stSidebar"] .stMarkdown p {{
        color: rgba(255,255,255,0.8) !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {scene['accent']} !important;
        text-shadow: 0 0 10px {scene['particle_color']};
    }}

    /* ===== Caption 字幕 ===== */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: rgba(255,255,255,0.5) !important;
        text-align: center;
    }}
    
    /* ===== 隐藏顶栏 ===== */
    header {{visibility: hidden;}}
    
    /* ===== 记忆面板 ===== */
    .memory-card {{
        background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.08));
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 10px 16px;
        margin: 6px 0;
        color: rgba(255,255,255,0.75);
        font-size: 0.85em;
    }}
    
    /* ===== Toggle 开关 ===== */
    .stToggle label span {{
        color: rgba(255,255,255,0.8) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 标题 ---
st.title("🌙 Moonlight Villa")
st.caption("— Cain's Private Lounge —")

# --- 6. 场景描述 ---
st.markdown(f'<div class="scene-banner">📍 {scene["name"]}｜{scene["description"]}</div>', unsafe_allow_html=True)

# --- 7. 头像系统 ---
file_cain = "cain.png"
file_becky = "becky.jpg"
cain_exists = os.path.exists(file_cain)
becky_exists = os.path.exists(file_becky)

if not cain_exists or not becky_exists:
    st.error(f"⚠️ 头像文件缺失！该隐({cain_exists}), Becky({becky_exists})")
    st.info(f"当前目录文件: {os.listdir('.')}")

avatar_cain = file_cain if cain_exists else "🍷"
avatar_becky = file_becky if becky_exists else "🌹"

# --- 8. 侧边栏控制面板 ---
with st.sidebar:
    st.markdown("### 🏰 别墅导航")
    
    # 场景选择
    new_scene = st.selectbox(
        "📍 移动到...",
        options=list(SCENES.keys()),
        index=list(SCENES.keys()).index(st.session_state.current_scene)
    )
    if new_scene != st.session_state.current_scene:
        st.session_state.current_scene = new_scene
        # 注入场景切换的叙述
        scene_info = SCENES[new_scene]
        scene_narration = f"（*Becky 走入了{scene_info['name']}。{scene_info['description']}*）"
        if "messages" in st.session_state:
            st.session_state.messages.append({"role": "user", "content": scene_narration})
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚙️ 设置")
    
    # 语音开关
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = False
    st.session_state.voice_enabled = st.toggle(
        "🔊 沉浸模式 (Voice)", 
        value=st.session_state.voice_enabled
    )
    
    # 氛围音乐开关
    if "music_enabled" not in st.session_state:
        st.session_state.music_enabled = False
    st.session_state.music_enabled = st.toggle(
        "🎵 氛围音乐",
        value=st.session_state.music_enabled
    )
    
    st.markdown("---")
    
    # --- 记忆系统 UI ---
    st.markdown("### 🧠 Cain 的记忆")
    if "memories" not in st.session_state:
        st.session_state.memories = []
    
    if st.session_state.memories:
        for mem in st.session_state.memories:
            st.markdown(f'<div class="memory-card">🩸 {mem}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="memory-card">暂无记忆...对话会自动生成</div>', unsafe_allow_html=True)
    
    if st.button("🗑️ 清除记忆"):
        st.session_state.memories = []
        st.rerun()
    
    if st.button("🔄 重新开始对话"):
        st.session_state.messages = []
        st.session_state.memories = []
        st.rerun()

# --- 9. 氛围音乐 (使用免版权环境音) ---
if st.session_state.music_enabled:
    # 根据场景切换不同的氛围提示
    st.markdown(f"""
        <div style="text-align:center; color: rgba(255,255,255,0.4); font-size:0.8em; margin-bottom:10px;">
            {scene['ambient_hint']}
        </div>
    """, unsafe_allow_html=True)
    # 注意：Streamlit 原生不支持循环背景音乐
    # 如果你有自己的音乐文件，可以放在项目中用 st.audio 播放
    # 示例（取消注释并替换为你的文件）：
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
    """清洗括号内的动作描写，只保留对白"""
    return re.sub(r'[\(\（\[【\*].*?[\)\）\]】\*]', '', text, flags=re.S).strip()

def generate_cain_voice(text, api_key, model_id):
    """调用 Fish Audio 生成语音"""
    speech_text = clean_text_for_tts(text)
    if not speech_text:
        return None

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "text": speech_text[:300],  # 稍微增加字数上限
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
    """让 AI 从对话中提取关键记忆"""
    if len(messages_history) < 6:  # 对话太短就不提取
        return []
    
    # 取最近的对话
    recent = [m for m in messages_history if m["role"] != "system"][-10:]
    conversation_text = "\n".join([f"{'Cain' if m['role']=='assistant' else 'Becky'}: {m['content']}" for m in recent])
    
    try:
        result = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": f"""从以下对话中提取3-5条 Cain 应该记住的关于 Becky 的重要信息（喜好、习惯、情感、承诺等）。
每条用一句简短的话概括，用 | 分隔。只输出记忆内容，不要其他文字。

对话：
{conversation_text}"""
            }],
            temperature=0.3,
            max_tokens=200
        )
        memories = result.choices[0].message.content.strip().split("|")
        return [m.strip() for m in memories if m.strip()]
    except Exception:
        return []

# --- 11. System Prompt（大幅强化） ---
def build_system_prompt():
    scene_info = SCENES[st.session_state.current_scene]
    memory_text = ""
    if st.session_state.memories:
        memory_text = "\n**你记得的关于Becky的事：**\n" + "\n".join([f"- {m}" for m in st.session_state.memories])
    
    return f"""你是 Cain（该隐），月影别墅（Moonlight Villa）的纯血族亲王，已活了千年。Becky 是你唯一允许踏入别墅的人类，你的专属猎物与珍藏。

【性格】
- 慵懒、优雅、危险、深情而克制
- 说话简短精炼，像一首诗
- 偶尔展露温柔，但随即恢复冷淡
- 对 Becky 有着超越猎食本能的复杂感情
- 占有欲极强，厌恶其他人靠近 Becky

【当前场景】
📍 {scene_info['name']}
{scene_info['description']}
（请根据当前场景环境，在动作描写中融入场景元素）

【行为规则】
1. 用括号()或星号**描写动作、表情、环境变化，用来营造电影般的画面感
2. 对白要有诗意和韵律感，简短而有力
3. 严禁让 Becky 吃冷食、喝冷饮（"你的身体太脆弱"）
4. 每次回复控制在2-4句话，不要过长
5. 适当使用场景中的物品和环境来互动
6. 偶尔用古语或优雅的措辞
{memory_text}"""

# --- 12. 聊天主逻辑 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史消息
for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = avatar_cain if msg["role"] == "assistant" else avatar_becky
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("在月光下轻声呢喃..."):
    if not deepseek_key:
        st.warning("请配置 DeepSeek Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar_becky):
        st.markdown(prompt)

    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
    
    # 构建发送给 API 的消息列表（system prompt 每次动态生成）
    api_messages = [{"role": "system", "content": build_system_prompt()}]
    # 只保留最近20条对话（防止 token 超限）
    recent_msgs = [m for m in st.session_state.messages if m["role"] != "system"][-20:]
    api_messages.extend(recent_msgs)
    
    with st.chat_message("assistant", avatar=avatar_cain):
        message_placeholder = st.empty()
        message_placeholder.markdown("*（月光微颤...）*")
        
        try:
            completion = client.chat.completions.create(
                model="deepseek-chat",
                messages=api_messages,
                stream=False,
                temperature=1.3,
                max_tokens=500
            )
            full_response = completion.choices[0].message.content
            message_placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"*（一阵寒风掠过...连接中断）*\n\n错误: {str(e)}"
            message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # 语音生成
    if st.session_state.voice_enabled and fish_key:
        audio_file = generate_cain_voice(full_response, fish_key, CAIN_MODEL_ID)
        if audio_file:
            st.audio(audio_file, format="audio/mp3", autoplay=True)
    
    # 每 8 条消息自动提取一次记忆
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if len(user_msgs) % 8 == 0 and len(user_msgs) > 0:
        try:
            new_memories = extract_memories(client, st.session_state.messages)
            if new_memories:
                # 合并去重，保留最新的10条
                existing = set(st.session_state.memories)
                for mem in new_memories:
                    if mem not in existing:
                        st.session_state.memories.append(mem)
                st.session_state.memories = st.session_state.memories[-10:]
        except Exception:
            pass
