import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os
import re  # 引入正则库，用来清洗括号

# --- 1. 配置区 ---
# 你的专属该隐 Model ID (Fish Audio)
CAIN_MODEL_ID = "a56e22a0ec34498da51cdb396f5fcb18"

# --- 2. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🍷", layout="centered")

# --- 3. 视觉魔法 (哥特磨砂玻璃风) ---
st.markdown("""
    <style>
    /* 1. 全局背景：深邃的午夜紫渐变 */
    .stApp {
        background: linear-gradient(135deg, #120024 0%, #320b54 50%, #4a148c 100%);
        background-attachment: fixed;
    }

    /* 2. 标题美化：发光的金色 */
    h1, h2, h3 {
        color: #E1BEE7 !important;
        font-family: 'Georgia', serif;
        text-shadow: 0 0 10px #7B1FA2;
    }
    
    /* 3. 聊天气泡：磨砂玻璃特效 (Glassmorphism) */
    /* 关键：背景是半透明白色 (0.9透明度)，字是深紫色，绝对清晰 */
    .stChatMessage {
        background-color: rgba(243, 229, 245, 0.95); 
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(4px);
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    
    /* 鼠标悬停时微微浮起，增加交互感 */
    .stChatMessage:hover {
        transform: translateY(-2px);
    }

    /* 4. 强制文字颜色为深紫，保证在磨砂玻璃上清晰可见 */
    .stChatMessage p, .stChatMessage div {
        color: #2E003E !important;
        font-weight: 500;
        font-family: 'Segoe UI', sans-serif;
    }

    /* 5. 输入框美化：发光边框 */
    .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.9);
        color: #2E003E !important;
        border: 2px solid #AB47BC;
        border-radius: 12px;
        box-shadow: 0 0 10px rgba(171, 71, 188, 0.3);
    }
    
    /* 6. 头像加个金边 */
    .stChatMessage .stAvatar {
        border: 2px solid #FFD700;
        box-shadow: 0 0 5px #FFD700;
    }
    
    /* 隐藏杂项 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 密钥读取 ---
if "DEEPSEEK_API_KEY" in st.secrets:
    deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    deepseek_key = st.sidebar.text_input("DeepSeek Key", type="password")

if "FISH_AUDIO_API_KEY" in st.secrets:
    fish_key = st.secrets["FISH_AUDIO_API_KEY"]
else:
    fish_key = st.sidebar.text_input("Fish Audio Key", type="password")

# --- 5. 核心逻辑：清洗括号 ---
def clean_text_for_tts(text):
    #
