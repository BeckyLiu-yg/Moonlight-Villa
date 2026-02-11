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

# 如果找不到图片，显示红
