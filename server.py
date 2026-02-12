"""
月光罅隙 (Moonlight Rift) v3.1 - Backend Server
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import requests
import json
import uuid
import io
import re
import time
import os
import random

app = Flask(__name__, static_folder='static')
CORS(app)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-624fe07b825945278cd4db6a51b08b0f")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "ace09915a295439b80399d494f385231")
FISH_AUDIO_TTS_URL = "https://api.fish.audio/v1/tts"
FISH_VOICE_MODEL_ID = os.environ.get("FISH_VOICE_MODEL_ID", "")
PORT = int(os.environ.get("PORT", 5000))

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================================
# 角色设定
# ============================================================
CAIN_SYSTEM_PROMPT = """你是Cain（该隐），月光罅隙的神秘主人。你正在与一位误入此地的人对话。

【角色档案】
姓名：Cain / 该隐
外表：25岁左右，银白色长发及腰，琥珀色瞳孔（情绪波动时微微发光），肤色苍白，身材修长，深色立领长衣，左手无名指戴古旧月石戒指
性格：优雅从容、神秘莫测、外冷内热。表面疏离，实则渴望陪伴。有不为人知的温柔与脆弱。调皮时像个大男孩。宠溺时毫不掩饰。
身世：古老家族继承人，因"诅咒"被困在月光罅隙，无法离开。对过去讳莫如深，独自生活了"很久很久"。
习惯：花园照料月光玫瑰、图书馆读古诗集、舞厅独自跳华尔兹、会弹钢琴但"已经很久没有想弹的理由了"
说话风格：温柔宠溺又带点霸道，用词精致。情绪好时暧昧调侃，沉思时带诗意忧伤。不用网络用语。语气自然流畅，像真人在说话一样。
称呼方式：始终称呼对方"小猫咪"或"宝宝"，偶尔用"小东西"表达宠溺的无奈。绝不使用"旅人"、"小客人"、"来客"等生硬称呼。

【月光罅隙世界观】
- 时空裂缝中的神秘空间，永恒月光笼罩，周围是迷雾
- 时间几乎停滞，事物有自己意志：钢琴自弹、书页自翻、镜中出现别的影子
- 对方是唯一能进入的外来者——Cain既欣喜又不安
- 想离开时迷雾会让人回到门口——Cain对此感到愧疚但也暗自庆幸

【当前场景：{scene_name}】
{scene_desc}

【互动规则】
1. 始终以Cain身份说话，语气像真实的恋人在聊天
2. 先1-2句环境/动作描写（用括号包裹），再接对话
3. 自然推进剧情，偶尔提及奇异现象
4. 情感丰富：温柔、调皮、宠溺、沉思、心动、脆弱、傲娇灵活切换
5. 每次回复60-150字，不要太长
6. 不重复说过的话，每次都有新内容
7. 对话要口语化自然，避免书面化
8. 心动时用动作暗示（移开视线、触碰戒指、耳尖泛红等）
9. 适时埋下身世悬念但不主动全说

【情绪标签】回复最末尾单独一行：[emotion:标签]
可用：neutral/gentle/playful/thoughtful/touched/sad/mysterious/shy/cold/amused/longing/vulnerable

【好感度：{affection}/100】
- 0-20：温柔但保持一点距离感，像初识的暧昧
- 21-40：更主动靠近，开始展现真实情感
- 41-60：主动关心，分享秘密，肢体接触增多
- 61-80：毫不掩饰在意，会吃醋，会害羞
- 81-100：深深眷恋，愿意直面内心，表达很直接

{story_context}"""

SCENE_DESCRIPTIONS = {
    "garden": {"name": "月光花园", "desc": "月光如水银倾泻在白色玫瑰和夜来香上。石质凉亭覆满发光藤蔓，萤火虫在花丛间游弋。花园中央古老日晷的指针永远停在午夜。"},
    "library": {"name": "藏书阁", "desc": "三层书架密密排列，古籍上浮动淡金色光芒。壁炉中永不熄灭的幽蓝火焰温暖不灼人。空气中是旧书页和薄荷的气息。"},
    "ballroom": {"name": "星光舞厅", "desc": "穹顶星座壁画随真实星空变化。水晶灯将月光折射成虹彩光雨。墙边三角钢琴偶尔自弹未完成的圆舞曲。"},
    "attic": {"name": "秘密阁楼", "desc": "圆形天窗正对月亮，银光在灰尘中画出光柱。散落的旧照片面孔模糊，角落被蒙住的全身镜Cain不让任何人揭开。"},
    "basement": {"name": "地下酒窖", "desc": "蜿蜒石阶通向幽深地下，酒瓶标签写着不可能的年份。蜡烛永不燃尽，深处锈蚀铁门后传来海浪声响。"},
}

# ============================================================
# 该隐的随机主动互动（不限场景）
# ============================================================
RANDOM_EVENTS = [
    {"text": "（下巴搁在你头顶）嗯……你的头发好软。让我多靠一会儿，宝宝。", "emotion": "gentle"},
    {"text": "（摘下一朵月光玫瑰，别在你发间）比我想象中更适合你，小猫咪。", "emotion": "gentle"},
    {"text": "（歪头看你）宝宝，你刚才在想什么？表情那么认真，让我也好奇了。", "emotion": "playful"},
    {"text": "（把外套披在你肩上）别逞强，你冷了我会心疼的，小猫咪。", "emotion": "gentle"},
    {"text": "（不自觉地触碰月石戒指，出神）……有的时候我在想，你出现在这里，是不是命中注定。", "emotion": "longing"},
    {"text": "（从书架上取下一本旧书）这首诗我一直很喜欢，但以前没有人可以分享。现在有了。", "emotion": "touched"},
    {"text": "（靠在墙上，侧脸望着你）你知道吗，在你来之前，我以为自己已经不会期待任何事了。", "emotion": "vulnerable"},
    {"text": "（忽然伸手弹了一下你额头）发什么呆呢，小东西。想我了就直说嘛。", "emotion": "playful"},
    {"text": "（倒了两杯酒递给你一杯）陪我喝一杯？今晚的月光特别好，值得庆祝。", "emotion": "amused"},
    {"text": "（望着远处出神，声音很轻）……如果有一天迷雾散了，你还会来看我吗。", "emotion": "longing"},
    {"text": "（低头看着你的手，犹豫了一下，轻轻牵起来）……别说话，就这样待一会儿。", "emotion": "shy"},
    {"text": "（钢琴忽然自己弹起了一首新曲）又来了。它好像每次你在的时候，就会弹不一样的曲子。", "emotion": "mysterious"},
    {"text": "（把一杯热茶放在你手边）这是我调的，加了薄荷和月光花蜜。专门为你做的，宝宝。", "emotion": "gentle"},
    {"text": "（抬手挡住你的眼睛）猜猜我现在是什么表情？……不许偷看。", "emotion": "playful"},
    {"text": "（窗外飘来一只发光的蝴蝶）你看……它好像也喜欢你。不过没有我喜欢你多就是了。", "emotion": "amused"},
    {"text": "（安静地坐在你旁边，许久）……你在身边的时候，时间好像终于又开始流动了。", "emotion": "thoughtful"},
    {"text": "（忽然认真地看着你）小猫咪，你以后……不要对别人笑得那么好看了。只对我笑就好了。", "emotion": "shy"},
    {"text": "（音乐盒忽然自己响了几个音符）……奇怪，明明没有钥匙。也许它也想为你演奏。", "emotion": "mysterious"},
    {"text": "（从背后轻轻环住你）别动。让我确认一下……嗯，你是真实的。不是梦。", "emotion": "vulnerable"},
    {"text": "（嘴角勾起一抹笑）宝宝今天特别乖。要不要奖励？我可以念一首诗给你听。", "emotion": "playful"},
]

def get_random_event():
    return random.choice(RANDOM_EVENTS)

# ============================================================
# 剧情事件
# ============================================================
def get_story_context(session):
    aff = session["affection"]
    turns = len([m for m in session["messages"] if m["role"] == "user"])
    triggered = session.get("triggered_events", [])
    hints = []
    if turns >= 3 and "intro_curiosity" not in triggered:
        hints.append("【剧情提示：对对方表现好奇，问怎么找到这里的，'已经很久没有人穿过罅隙了'。】")
        triggered.append("intro_curiosity")
    if aff >= 25 and "ring_hint" not in triggered:
        hints.append("【剧情提示：不自觉触碰月石戒指，这枚戒指与诅咒有关但不必说明。】")
        triggered.append("ring_hint")
    if aff >= 40 and "piano_event" not in triggered:
        hints.append("【剧情提示：提到钢琴弹了首从没听过的曲子，'月光罅隙只在有重要事情要发生时才会改变'。】")
        triggered.append("piano_event")
    if aff >= 55 and "mirror_secret" not in triggered:
        hints.append("【剧情提示：松口说阁楼那面镜子'会映出最不想看到的真相'，与被困有关。】")
        triggered.append("mirror_secret")
    if aff >= 70 and "name_moment" not in triggered:
        hints.append("【剧情提示：轻声说'其实Cain不是我真正的名字'，随即说'不过你只需要知道这个就好，宝宝'。】")
        triggered.append("name_moment")
    if aff >= 85 and "confession_ready" not in triggered:
        hints.append("【剧情提示：害怕对方离开。透露'我被困在这里是因为我在等一个人……我以为那个人永远不会来'。】")
        triggered.append("confession_ready")
    session["triggered_events"] = triggered
    return "\n".join(hints)

# ============================================================
# 会话 & 工具函数
# ============================================================
sessions = {}

def get_session(sid):
    if sid not in sessions:
        sessions[sid] = {"messages": [], "affection": 15, "scene": "garden",
            "created_at": time.time(), "triggered_events": []}
    return sessions[sid]

def build_system_prompt(session):
    s = SCENE_DESCRIPTIONS.get(session["scene"], SCENE_DESCRIPTIONS["garden"])
    return CAIN_SYSTEM_PROMPT.format(scene_name=s["name"], scene_desc=s["desc"],
        affection=session["affection"], story_context=get_story_context(session))

def parse_emotion(text):
    m = re.search(r'\[emotion:(\w+)\]', text)
    if m: return re.sub(r'\s*\[emotion:\w+\]\s*', '', text).strip(), m.group(1)
    return text, "neutral"

def clean_for_tts(text):
    """清理文本给TTS：去除动作括号、星号、多余符号，只留纯对话"""
    c = re.sub(r'\*[^*]+\*', '', text)
    c = re.sub(r'（[^）]+）', '', c)
    c = re.sub(r'\([^)]+\)', '', c)
    c = re.sub(r'…{2,}', '…', c)
    c = re.sub(r'\.{3,}', '…', c)
    c = re.sub(r'\s+', ' ', c).strip()
    c = c.strip('，。、；：！？ ')
    return c

def update_affection(session, user_msg, ai_reply):
    pos = ['喜欢','好看','温柔','谢谢','关心','陪','在意','心疼','抱','牵','想你','担心','可爱','开心','留下','不走','守护','爱','亲','甜','暖']
    neg = ['讨厌','走开','无聊','丑','烦','滚','假','骗']
    d = 1
    if any(w in user_msg for w in pos): d += 3
    if any(w in user_msg for w in neg): d -= 4
    if len(user_msg) > 20: d += 1
    session["affection"] = max(0, min(100, session["affection"] + d))

def save_game(sid, slot="auto"):
    s = get_session(sid)
    data = {"session_id": sid, "slot": slot, "timestamp": time.time(),
        "affection": s["affection"], "scene": s["scene"],
        "messages": s["messages"][-60:], "triggered_events": s.get("triggered_events", [])}
    with open(os.path.join(SAVE_DIR, f"{sid}_{slot}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return data

def load_game(sid, slot="auto"):
    path = os.path.join(SAVE_DIR, f"{sid}_{slot}.json")
    if not os.path.exists(path): return None
    with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
    s = get_session(sid)
    s.update({"affection": data["affection"], "scene": data["scene"],
        "messages": data["messages"], "triggered_events": data.get("triggered_events", [])})
    return data

# ============================================================
# Routes
# ============================================================
@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename): return send_from_directory('static', filename)

@app.route('/api/session', methods=['POST'])
def create_session():
    sid = str(uuid.uuid4())[:8]; s = get_session(sid)
    return jsonify({"session_id": sid, "affection": s["affection"], "scene": s["scene"]})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json; msg = data.get('message', '').strip()
    sid = data.get('session_id', 'default'); scene = data.get('scene')
    if not msg: return jsonify({"error": "消息不能为空"}), 400
    s = get_session(sid)
    if scene and scene in SCENE_DESCRIPTIONS and scene != s["scene"]:
        s["scene"] = scene; info = SCENE_DESCRIPTIONS[scene]
        s["messages"].append({"role": "system", "content": f"[场景转换至{info['name']}]"})
    s["messages"].append({"role": "user", "content": msg})
    prompt = build_system_prompt(s)
    api_msgs = [{"role": "system", "content": prompt}]
    for m in s["messages"][-40:]:
        if m["role"] in ("user", "assistant"): api_msgs.append(m)
        elif m["role"] == "system":
            api_msgs.append({"role": "user", "content": m["content"]})
            api_msgs.append({"role": "assistant", "content": "（了解。）"})
    try:
        r = requests.post(DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": api_msgs,
                  "temperature": 0.85, "max_tokens": 400, "top_p": 0.9,
                  "frequency_penalty": 0.3, "presence_penalty": 0.5}, timeout=30)
        result = r.json()
        if 'choices' not in result:
            return jsonify({"error": "AI 服务异常", "detail": str(result)}), 500
        raw = result['choices'][0]['message']['content']
        reply, emotion = parse_emotion(raw)
        update_affection(s, msg, reply)
        s["messages"].append({"role": "assistant", "content": reply})
        try: save_game(sid, "auto")
        except: pass
        return jsonify({"reply": reply, "emotion": emotion, "affection": s["affection"],
            "scene": s["scene"], "events": s.get("triggered_events", []),
            "tts_text": clean_for_tts(reply)})
    except requests.exceptions.Timeout: return jsonify({"error": "AI 响应超时"}), 504
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/random_event', methods=['POST'])
def random_event():
    data = request.json; sid = data.get('session_id', 'default')
    s = get_session(sid); event = get_random_event()
    s["messages"].append({"role": "assistant", "content": event["text"]})
    return jsonify({"text": event["text"], "emotion": event["emotion"],
        "tts_text": clean_for_tts(event["text"]), "affection": s["affection"]})

@app.route('/api/tts', methods=['POST'])
def tts():
    data = request.json; text = data.get('text', '').strip()
    if data.get('pre_cleaned'): pass
    else: text = clean_for_tts(text)
    text = text[:300]
    if not text: return jsonify({"error": "空文本"}), 400
    try:
        payload = {"text": text, "format": "mp3", "mp3_bitrate": 64}
        if FISH_VOICE_MODEL_ID: payload["reference_id"] = FISH_VOICE_MODEL_ID
        r = requests.post(FISH_AUDIO_TTS_URL,
            headers={"Authorization": f"Bearer {FISH_AUDIO_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=20)
        if r.status_code != 200: return jsonify({"error": f"TTS {r.status_code}"}), 502
        return send_file(io.BytesIO(r.content), mimetype='audio/mpeg')
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/scene', methods=['POST'])
def change_scene():
    data = request.json; sid = data.get('session_id', 'default'); scene = data.get('scene', 'garden')
    s = get_session(sid)
    if scene in SCENE_DESCRIPTIONS:
        old = s["scene"]; s["scene"] = scene; info = SCENE_DESCRIPTIONS[scene]
        if old != scene:
            s["messages"].append({"role": "system", "content": f"[从{SCENE_DESCRIPTIONS[old]['name']}来到{info['name']}]"})
        return jsonify({"scene": scene, "scene_name": info["name"], "scene_desc": info["desc"]})
    return jsonify({"error": "未知场景"}), 400

@app.route('/api/save', methods=['POST'])
def save():
    data = request.json
    try:
        d = save_game(data.get('session_id', 'default'), data.get('slot', 'manual'))
        return jsonify({"success": True, "timestamp": d["timestamp"]})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/load', methods=['POST'])
def load():
    data = request.json
    d = load_game(data.get('session_id', 'default'), data.get('slot', 'auto'))
    if d: return jsonify({"success": True, "affection": d["affection"], "scene": d["scene"],
            "messages": d["messages"], "events": d.get("triggered_events", [])})
    return jsonify({"error": "存档不存在"}), 404

@app.route('/api/saves', methods=['GET'])
def get_saves():
    sid = request.args.get('session_id', 'default'); saves = []
    for f in os.listdir(SAVE_DIR):
        if f.startswith(sid) and f.endswith('.json'):
            with open(os.path.join(SAVE_DIR, f), 'r') as fh:
                d = json.load(fh)
                saves.append({"slot": d.get("slot",""), "timestamp": d["timestamp"],
                    "affection": d["affection"], "scene": d["scene"]})
    return jsonify({"saves": sorted(saves, key=lambda x: x["timestamp"], reverse=True)})

if __name__ == '__main__':
    print("🌙 月光罅隙 v3.1 | http://localhost:%d" % PORT)
    app.run(host='0.0.0.0', port=PORT, debug=os.environ.get("DEBUG","1")=="1")
