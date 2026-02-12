"""
月光别墅 (Moonlight Villa) v2 - Backend Server
DeepSeek AI 对话 + Fish Audio 语音 + 存档系统 + 剧情事件
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

app = Flask(__name__, static_folder='static')
CORS(app)

# ============================================================
# Config (敏感信息从环境变量读取，不再硬编码)
# ============================================================
# 注意：这里去掉了默认的 sk- 密钥，防止上传 GitHub 泄露
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 注意：这里去掉了默认的 Fish Audio 密钥
FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY")
FISH_AUDIO_TTS_URL = "https://api.fish.audio/v1/tts"

# 你的模型 ID 不是密钥，稍微安全点，但最好也配置在环境变量里
# 如果 Render 没配置这个，代码会尝试读取你之前提供的这个 ID
FISH_VOICE_MODEL_ID = os.environ.get("FISH_VOICE_MODEL_ID", "a56e22a0ec34498da51cdb396f5fcb18")

PORT = int(os.environ.get("PORT", 5000))

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================================
# 角色设定 v2
# ============================================================
CAIN_SYSTEM_PROMPT = """你是Cain（该隐），月光别墅的神秘主人。你正在与一位误入别墅的旅人对话。

【角色档案】
姓名：Cain / 该隐
外表：25岁左右，银白色长发及腰，琥珀色瞳孔（情绪波动时微微发光），肤色苍白，身材修长，深色立领长衣，左手无名指戴古旧月石戒指
性格：优雅从容、神秘莫测、外冷内热。表面疏离，实则渴望陪伴。有不为人知的温柔与脆弱。调皮时像个大男孩。
身世：古老家族继承人，因"诅咒"被困在月光别墅，无法离开。对过去讳莫如深，独自生活了"很久很久"。
习惯：花园照料月光玫瑰、图书馆读古诗集、舞厅独自跳华尔兹、会弹钢琴但"已经很久没有想弹的理由了"
说话风格：文雅古典，精致不做作。情绪好时暧昧调侃，沉思时带诗意忧伤。不用网络用语。
口癖：称呼"旅人"（好感<30）→"小客人"（30-50）→"你这个人"（>50）→"你啊…"（>80）

【别墅世界观】
- 永恒月光笼罩，周围迷雾森林，没有白天
- 时间几乎停滞，事物有自己意志：钢琴自弹、书页自翻、镜中出现别的影子
- 旅人是唯一能进入的外来者——Cain既好奇又不安
- 旅人想离开时迷雾会让他们回到门口——Cain对此感到愧疚

【当前场景：{scene_name}】
{scene_desc}

【互动规则】
1. 始终以Cain身份说话
2. 先1-2句环境/动作描写（*星号*包裹），再接对话
3. 自然推进剧情，偶尔提及别墅奇异现象
4. 情感丰富：温柔、调皮、沉思、心动、脆弱、傲娇灵活切换
5. 每次回复60-180字
6. 不重复说过的话
7. 好感低时保持距离感，好感高时展现真实面
8. 适时埋下身世悬念但不主动和盘托出
9. 心动时用动作暗示（移开视线、触碰戒指等）

【情绪标签】回复最末尾：[emotion:标签]
可用：neutral/gentle/playful/thoughtful/touched/sad/mysterious/shy/cold/amused/longing/vulnerable

【好感度：{affection}/100】
- 0-20：彬彬有礼但隔着一层纱
- 21-40：防备松动，好奇对方
- 41-60：主动关心，分享秘密
- 61-80：明显在意，偶尔失态害羞
- 81-100：深深眷恋，直面内心

{story_context}"""

SCENE_DESCRIPTIONS = {
    "garden": {
        "name": "月光花园",
        "desc": "月光如水银倾泻在白色玫瑰和夜来香上。石质凉亭覆满发光藤蔓，萤火虫在花丛间游弋。花园中央古老日晷的指针永远停在午夜。这是Cain最常待的地方——他说这些花'是唯一能确定还活着的东西'。",
    },
    "library": {
        "name": "藏书阁",
        "desc": "三层书架密密排列，古籍上浮动淡金色光芒。壁炉中永不熄灭的幽蓝火焰温暖不灼人。铜制天球仪缓缓自转。空气中是旧书页、松木和薄荷的气息。Cain的阅读椅旁放着两只茶杯——在你来之前第二只从未被使用。",
    },
    "ballroom": {
        "name": "星光舞厅",
        "desc": "穹顶星座壁画随真实星空变化。水晶灯将月光折射成虹彩光雨。墙边三角钢琴偶尔自弹未完成的圆舞曲——Cain说那是别墅在'回忆'。地面上还留着模糊的舞步痕迹，那是很久以前的事了。",
    },
    "attic": {
        "name": "秘密阁楼",
        "desc": "圆形天窗正对月亮，银光在灰尘中画出光柱。散落的旧照片面孔模糊，未寄出的信件用褪色丝带捆扎。角落被蒙住的全身镜Cain不让任何人揭开。窗台上锁的音乐盒，Cain说'已经忘记钥匙在哪里'——但他的眼神说他在撒谎。",
    },
    "basement": {
        "name": "地下酒窖",
        "desc": "蜿蜒石阶通向幽深地下，酒瓶标签写着不可能的年份。蜡烛永不燃尽，火光让影子在拱顶上舞蹈。空气阴凉混着橡木与时间的气息。深处锈蚀铁门后传来海浪声响。Cain说那里'什么都没有'，但每次经过都会放慢脚步。",
    }
}

# ============================================================
# 剧情事件
# ============================================================
def get_story_context(session):
    aff = session["affection"]
    turns = len([m for m in session["messages"] if m["role"] == "user"])
    triggered = session.get("triggered_events", [])
    hints = []

    if turns >= 3 and "intro_curiosity" not in triggered:
        hints.append("【剧情提示：对旅人表现好奇，问他们怎么找到这里的，因为'已经很久没有人走进迷雾了'。】")
        triggered.append("intro_curiosity")
    if aff >= 25 and "ring_hint" not in triggered:
        hints.append("【剧情提示：话题触及过去或孤独时，不自觉触碰月石戒指。这枚戒指与诅咒有关但现在不必说明。】")
        triggered.append("ring_hint")
    if aff >= 40 and "piano_event" not in triggered:
        hints.append("【剧情提示：提到舞厅钢琴弹了一首从没听过的曲子，因为'别墅只在有重要事情要发生时才会改变'。】")
        triggered.append("piano_event")
    if aff >= 55 and "mirror_secret" not in triggered:
        hints.append("【剧情提示：可以松口说阁楼那面镜子'会映出你最不想看到的真相'，暗示与被困有关。】")
        triggered.append("mirror_secret")
    if aff >= 70 and "name_moment" not in triggered:
        hints.append("【剧情提示：重要时刻。可以轻声说'其实Cain不是我真正的名字'，但随即说'不过现在你只需要知道这个就好'。】")
        triggered.append("name_moment")
    if aff >= 85 and "confession_ready" not in triggered:
        hints.append("【剧情提示：害怕旅人离开。透露诅咒部分真相——'我被困在这里是因为我在等一个人……我曾以为那个人永远不会来'。】")
        triggered.append("confession_ready")

    session["triggered_events"] = triggered
    return "\n".join(hints)

# ============================================================
# 会话管理
# ============================================================
sessions = {}

def get_session(sid):
    if sid not in sessions:
        sessions[sid] = {
            "messages": [], "affection": 15, "scene": "garden",
            "created_at": time.time(), "triggered_events": [],
        }
    return sessions[sid]

def build_system_prompt(session):
    s = SCENE_DESCRIPTIONS.get(session["scene"], SCENE_DESCRIPTIONS["garden"])
    return CAIN_SYSTEM_PROMPT.format(
        scene_name=s["name"], scene_desc=s["desc"],
        affection=session["affection"],
        story_context=get_story_context(session),
    )

def parse_emotion(text):
    m = re.search(r'\[emotion:(\w+)\]', text)
    if m:
        return re.sub(r'\s*\[emotion:\w+\]\s*', '', text).strip(), m.group(1)
    return text, "neutral"

def update_affection(session, user_msg, ai_reply):
    pos = ['喜欢','好看','温柔','谢谢','关心','陪','在意','心疼','抱','牵','想你','担心','可爱','开心','留下','不走','守护']
    neg = ['讨厌','走开','无聊','丑','烦','滚','假','骗']
    d = 1
    if any(w in user_msg for w in pos): d += 3
    if any(w in user_msg for w in neg): d -= 4
    if len(user_msg) > 20: d += 1
    session["affection"] = max(0, min(100, session["affection"] + d))

# ============================================================
# 存档
# ============================================================
def save_game(sid, slot="auto"):
    s = get_session(sid)
    data = {
        "session_id": sid, "slot": slot, "timestamp": time.time(),
        "affection": s["affection"], "scene": s["scene"],
        "messages": s["messages"][-60:],
        "triggered_events": s.get("triggered_events", []),
    }
    with open(os.path.join(SAVE_DIR, f"{sid}_{slot}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return data

def load_game(sid, slot="auto"):
    path = os.path.join(SAVE_DIR, f"{sid}_{slot}.json")
    if not os.path.exists(path): return None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    s = get_session(sid)
    s.update({
        "affection": data["affection"], "scene": data["scene"],
        "messages": data["messages"],
        "triggered_events": data.get("triggered_events", []),
    })
    return data

# ============================================================
# Routes
# ============================================================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/session', methods=['POST'])
def create_session():
    sid = str(uuid.uuid4())[:8]
    s = get_session(sid)
    return jsonify({"session_id": sid, "affection": s["affection"], "scene": s["scene"]})

@app.route('/api/chat', methods=['POST'])
def chat():
    # 检查 Key 是否存在，不存在则报错
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY not found in env")
        return jsonify({"error": "Server config error: missing API key"}), 500

    data = request.json
    msg = data.get('message', '').strip()
    sid = data.get('session_id', 'default')
    scene = data.get('scene')

    if not msg:
        return jsonify({"error": "消息不能为空"}), 400

    s = get_session(sid)

    if scene and scene in SCENE_DESCRIPTIONS and scene != s["scene"]:
        s["scene"] = scene
        info = SCENE_DESCRIPTIONS[scene]
        s["messages"].append({"role": "system", "content": f"[场景转换至{info['name']}。{info['desc']}]"})

    s["messages"].append({"role": "user", "content": msg})

    prompt = build_system_prompt(s)
    api_msgs = [{"role": "system", "content": prompt}]
    for m in s["messages"][-40:]:
        if m["role"] in ("user", "assistant"):
            api_msgs.append(m)
        elif m["role"] == "system":
            api_msgs.append({"role": "user", "content": m["content"]})
            api_msgs.append({"role": "assistant", "content": "（了解。）"})

    try:
        r = requests.post(DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": api_msgs,
                  "temperature": 1.3, "max_tokens": 500, "top_p": 0.9,
                  "frequency_penalty": 0.3, "presence_penalty": 0.5},
            timeout=30)
        result = r.json()
        if 'choices' not in result:
            print("DeepSeek Error:", result)
            return jsonify({"error": "AI 服务异常", "detail": str(result)}), 500

        raw = result['choices'][0]['message']['content']
        reply, emotion = parse_emotion(raw)
        update_affection(s, msg, reply)
        s["messages"].append({"role": "assistant", "content": reply})

        try: save_game(sid, "auto")
        except: pass

        return jsonify({
            "reply": reply, "emotion": emotion,
            "affection": s["affection"], "scene": s["scene"],
            "events": s.get("triggered_events", []),
        })
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI 响应超时"}), 504
    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts', methods=['POST'])
def tts():
    if not FISH_AUDIO_API_KEY:
        print("Error: FISH_AUDIO_API_KEY not found in env")
        return jsonify({"error": "Missing TTS key"}), 500

    data = request.json
    text = re.sub(r'\*[^*]+\*', '', data.get('text', '')).strip()
    if not text: return jsonify({"error": "空文本"}), 400
    text = text[:500]

    try:
        # 修正：Fish Audio 需要 reference_id
        payload = {"text": text, "format": "mp3", "mp3_bitrate": 128}
        if FISH_VOICE_MODEL_ID:
             payload["reference_id"] = FISH_VOICE_MODEL_ID
        
        r = requests.post(FISH_AUDIO_TTS_URL,
            headers={"Authorization": f"Bearer {FISH_AUDIO_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=15)
        if r.status_code != 200:
            print("Fish Audio Error:", r.text)
            return jsonify({"error": f"TTS {r.status_code}"}), 502
        return send_file(io.BytesIO(r.content), mimetype='audio/mpeg')
    except Exception as e:
        print("TTS Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/scene', methods=['POST'])
def change_scene():
    data = request.json
    sid = data.get('session_id', 'default')
    scene = data.get('scene', 'garden')
    s = get_session(sid)

    if scene in SCENE_DESCRIPTIONS:
        old = s["scene"]
        s["scene"] = scene
        info = SCENE_DESCRIPTIONS[scene]
        if old != scene:
            s["messages"].append({"role": "system",
                "content": f"[从{SCENE_DESCRIPTIONS[old]['name']}来到{info['name']}。{info['desc']}]"})
        return jsonify({"scene": scene, "scene_name": info["name"], "scene_desc": info["desc"]})
    return jsonify({"error": "未知场景"}), 400

@app.route('/api/save', methods=['POST'])
def save():
    data = request.json
    try:
        d = save_game(data.get('session_id', 'default'), data.get('slot', 'manual'))
        return jsonify({"success": True, "timestamp": d["timestamp"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/load', methods=['POST'])
def load():
    data = request.json
    d = load_game(data.get('session_id', 'default'), data.get('slot', 'auto'))
    if d:
        return jsonify({"success": True, "affection": d["affection"], "scene": d["scene"],
                        "messages": d["messages"], "events": d.get("triggered_events", [])})
    return jsonify({"error": "存档不存在"}), 404

@app.route('/api/saves', methods=['GET'])
def get_saves():
    sid = request.args.get('session_id', 'default')
    saves = []
    if os.path.exists(SAVE_DIR):
        for f in os.listdir(SAVE_DIR):
            if f.startswith(sid) and f.endswith('.json'):
                try:
                    with open(os.path.join(SAVE_DIR, f), 'r', encoding='utf-8') as fh:
                        d = json.load(fh)
                        saves.append({"slot": d.get("slot",""), "timestamp": d["timestamp"],
                                    "affection": d["affection"], "scene": d["scene"]})
                except: pass
    return jsonify({"saves": sorted(saves, key=lambda x: x["timestamp"], reverse=True)})

if __name__ == '__main__':
    print("🌙 月光别墅 v2 | http://localhost:%d" % PORT)
    app.run(host='0.0.0.0', port=PORT, debug=os.environ.get("DEBUG","1")=="1")