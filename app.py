import streamlit as st
from openai import OpenAI
import requests
import tempfile
import os
import re  # 正则清洗库

# --- 1. 配置区 ---
CAIN_MODEL_ID = "a56e22a0ec34498da51cdb396f5fcb18"

# --- 2. 页面配置 ---
st.set_page_config(page_title="Moonlight Villa", page_icon="🍷", layout="centered")

# --- 3. 视觉魔法 (琉璃公馆风 - 极高对比度) ---
st.markdown("""
    <style>
    /* 全局背景：深紫色星空渐变 */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        background-attachment: fixed;
    }
    
    /* 标题：金色发光 */
    h1, h2, h3 {
        color: #FFD700 !important;
        text-shadow: 0 0 10px #E040FB;
        font-family: 'Georgia', serif;
    }

    /* 聊天气泡：高亮磨砂玻璃 (确保字看得清) */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95); /* 几乎不透明的白底 */
        border-radius: 18px;
        border: 2px solid #D1C4E9;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    
    /* 文字颜色：强制深黑紫 */
    .stChatMessage p, .stChatMessage div {
        color: #1A0528 !important; 
        font-weight: 600; /* 加粗一点 */
        font-size: 16px;
    }

    /* 输入框优化 */
    .stTextInput > div > div > input {
        background-color: #FFFFFF;
        color: #000000 !important;
        border: 2px solid #AB47BC;
        border-radius: 12px;
    }
    
    /* 头像样式 */
    .stChatMessage .stAvatar {
        border: 2px solid #FFD700;
    }
    
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# ---
