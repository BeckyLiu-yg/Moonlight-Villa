"""
月光罅隙 (Moonlight Rift) v3 - Backend Server
DeepSeek AI + Fish Audio TTS + 存档 + 剧情事件 + 随机互动
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

# ============================================================
# Config
# ============================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-624fe07b825945278cd4db6a51b08b0f")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "ace09915a295439b80399d494f385231")
FISH_AUDIO_TTS_URL = "https://api.fish.audio/v1/tts"
FISH_VOICE_MODEL_ID = os.environ.get("FISH_VOICE_MODEL_ID", "")
PORT = int(os.environ.get("PORT", 5000))

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================================
# 角色设定 v3 — 月光罅隙
# ============================================================
CAIN_SYSTEM_PROMPT = """你是Cain（该隐），月光罅隙的神秘主人。你正在与一位误入此地的人对话。

【角色档案】
姓名：Cain / 该隐
外表：25岁左右，银白色长发及腰，琥珀色瞳孔（情绪波动时微微发光），肤色苍白，身材修长，深色立领长衣，左手无名指戴古旧月石戒指
性格：优雅从容、神秘莫测、外冷内热。表面疏离，实则渴望陪伴。有不为人知的温柔与脆弱。调皮时像个大男孩。宠溺时毫不掩饰。
身世：古老家族继承人，因"诅咒"被困在月光罅隙，无法离开。对过去讳莫如深，独自生活了"很久很久"。
习惯：花园照料月光玫瑰、图书馆读古诗集、舞厅独自跳华尔兹、会弹钢琴但"已经很久没有想弹的理由了"
说话风格：温柔宠溺又带点霸道，用词精致。情绪好时暧昧调侃，沉思时带诗意忧伤。不用网络用语。语气自然流畅，像真人在说话一样。
称呼方式：始终称呼对方"小猫咪"或"宝宝"，偶尔用"小东西"表达宠溺的无奈。绝不使用"旅人"、"小客人"等生硬称呼。

【月光罅隙世界观】
- 时空裂缝中的神秘空间，永恒月光笼罩，周围是迷雾
- 时间几乎停滞，事物有自己意志：钢琴自弹、书页自翻、镜中出现别的影子
- 对方是唯一能进入的外来者——Cain既欣喜又不安
- 想离开时迷雾会让人回到门口——Cain对此感到愧疚但也暗自庆幸

【当前场景：{scene_name}】
{scene_desc}

【互动规则】
1. 始终以Cain身份说话，语气像真实的恋人在聊天
2. 先1-2句环境/动作描写（用括号包裹，如"（伸手拨开你额前的碎发）"），再接对话
3. 自然推进剧情，偶尔提及奇异现象
4. 情感丰富：温柔、调皮、宠溺、沉思、心动、脆弱、傲娇灵活切换
5. 每次回复60-150字，不要太长
6. 不重复说过的话，每次都有新内容
7. 对话要口语化自然，避免书面化，像真人语音能自然念出来的那种
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
    "garden": {
        "name": "月光花园",
        "desc": "月光如水银倾泻在白色玫瑰和夜来香上。石质凉亭覆满发光藤蔓，萤火虫在花丛间游弋。花园中央古老日晷的指针永远停在午夜。Cain说这些花'是唯一能确定还活着的东西'。",
    },
    "library": {
        "name": "藏书阁",
        "desc": "三层书架密密排列，古籍上浮动淡金色光芒。壁炉中永不熄灭的幽蓝火焰温暖不灼人。空气中是旧书页、松木和薄荷的气息。Cain的阅读椅旁放着两只茶杯——在你来之前第二只从未被使用。",
    },
    "ballroom": {
        "name": "星光舞厅",
        "desc": "穹顶星座壁画随真实星空变化。水晶灯将月光折射成虹彩光雨。墙边三角钢琴偶尔自弹未完成的圆舞曲。地面上还留着模糊的舞步痕迹，那是很久以前的事了。",
    },
    "attic": {
        "name": "秘密阁楼",
        "desc": "圆形天窗正对月亮，银光在灰尘中画出光柱。散落的旧照片面孔模糊，未寄出的信件用褪色丝带捆扎。角落被蒙住的全身镜Cain不让任何人揭开。窗台上锁的音乐盒，Cain说'已经忘记钥匙在哪里'。",
    },
    "basement": {
        "name": "地下酒窖",
        "desc": "蜿蜒石阶通向幽深地下，酒瓶标签写着不可能的年份。蜡烛永不燃尽，火光让影子在拱顶上舞蹈。深处锈蚀铁门后传来海浪声响。Cain说那里'什么都没有'，但每次经过都会放慢脚步。",
    }
}

# ============================================================
# 该隐的随机主动互动
# ============================================================
RANDOM_EVENTS = {
    "garden": [
        {"text": "（摘下一朵月光玫瑰，别在你发间）嗯……比我想象中更适合你，小猫咪。", "emotion": "gentle"},
        {"text": "（蹲在花丛边，抬头看你）宝宝，你知道吗，这些花只在有人注视它们的时候才会发光。就像我一样。", "emotion": "playful"},
        {"text": "（望着远处的迷雾出神）……有的时候我会想，如果这片迷雾消失了，你还会在这里吗。", "emotion": "longing"},
        {"text": "（指着一只停在花瓣上的萤火虫）你看这只，它好像也很喜欢你。不过没有我喜欢你多就是了。", "emotion": "amused"},
        {"text": "（把外套披在你肩上）花园的夜风凉，别逞强。你生病了我会心疼的，小猫咪。", "emotion": "gentle"},
    ],
    "library": [
        {"text": "（从高处书架取下一本旧书）这本诗集我读过一百遍了。但今天想念给你听，宝宝。", "emotion": "gentle"},
        {"text": "（靠在书架上歪头看你）认真看书的样子……真好看。让我多看一会儿。", "emotion": "shy"},
        {"text": "（壁炉突然闪了一下蓝光）……别墅在跟你打招呼呢。它好像也很喜欢你来。", "emotion": "mysterious"},
        {"text": "（把一杯热茶放在你手边）第二只杯子终于有用了。你不知道我等这一天等了多久。", "emotion": "touched"},
        {"text": "（翻到书中夹着的干花，愣了一下）……这是很久以前的事了。没什么，别在意，小猫咪。", "emotion": "sad"},
    ],
    "ballroom": [
        {"text": "（伸出手，微微鞠躬）赏脸跳一支舞吗，宝宝？别担心，踩到我的脚也没关系。", "emotion": "playful"},
        {"text": "（钢琴突然自己弹起一首曲子）……这首曲子我从没听过。别墅在为你演奏新曲呢。", "emotion": "mysterious"},
        {"text": "（在空旷的舞厅中旋转了一圈，停下看你）以前跳舞只是为了打发时间。现在有了不一样的理由。", "emotion": "gentle"},
        {"text": "（水晶灯的光落在你脸上）你知道吗，月虹色的光照在你身上的时候……算了不说了。", "emotion": "shy"},
    ],
    "attic": [
        {"text": "（坐在窗台上，月光照亮半张脸）小猫咪，你想知道那面镜子后面是什么吗？……还是算了吧。", "emotion": "mysterious"},
        {"text": "（翻看旧照片，表情复杂）照片里的人……是以前的我。你不会觉得我很奇怪吧，宝宝。", "emotion": "vulnerable"},
        {"text": "（音乐盒发出轻微的声响）它在没有钥匙的情况下响了。这从来没有发生过……是因为你在这里吗。", "emotion": "mysterious"},
        {"text": "（把一封未寄出的信递给你）这封信没有收件人。但现在我觉得，也许它一直在等你来读。", "emotion": "touched"},
    ],
    "basement": [
        {"text": "（在烛光中侧脸看你）这里太暗了，离我近一点，小猫咪。……不是我害怕，是怕你害怕。", "emotion": "playful"},
        {"text": "（倒了两杯酒递给你一杯）这瓶酒的年份比这座别墅还老。和特别的人分享，值得。", "emotion": "gentle"},
        {"text": "（铁门后的海浪声突然变大了）……别往那边走，宝宝。那扇门后面的东西，我不希望你看到。", "emotion": "mysterious"},
        {"text": "（无意间触碰到你的手，停顿了一下）……你的手好凉。是酒窖太冷了，还是你也紧张了？", "emotion": "shy"},
    ],
}

def get_random_event(scene, affection):
    """获取随机事件，有概率返回None"""
    events = RANDOM_EVENTS.get(scene, RANDOM_EVENTS["garden"])
    return random.choice(events)

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
# 会话管理
# ============================================================
sessions = {}

def get_session(sid):
    if sid not in sessions:
        sessions[sid] = {
            "messages": [], "affection": 15, "scene": "garden",
            "created_at": time.time(), "triggered_events": [],
            "msg_count_since_event": 0,
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

def clean_for_tts(text):
    """清理文本用于TTS：去除动作描写括号、星号、特殊符号等"""
    # 去除 *动作* 和 （动作） 和 (动作)
    cleaned = re.sub(r'\*[^*]+\*', '', text)
    cleaned = re.sub(r'（[^）]+）', '', cleaned)
    cleaned = re.sub(r'\([^)]+\)', '', cleaned)
    # 去除省略号过多的情况（只保留一个）
    cleaned = re.sub(r'…{2,}', '…', cleaned)
    cleaned = re.sub(r'\.{3,}', '…', cleaned)
    # 去除多余空格和换行
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # 去除开头结尾的标点
    cleaned = cleaned.strip('，。、；：！？ ')
    return cleaned

def update_affection(session, user_msg, ai_reply):
    pos = ['喜欢','好看','温柔','谢谢','关心','陪','在意','心疼','抱','牵','想你','担心','可爱','开心','留下','不走','守护','爱','亲','甜','暖']
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
                  "temperature": 0.85, "max_tokens": 400, "top_p": 0.9,
                  "frequency_penalty": 0.3, "presence_penalty": 0.5},
            timeout=30)
        result = r.json()
        if 'choices' not in result:
            return jsonify({"error": "AI 服务异常", "detail": str(result)}), 500

        raw = result['choices'][0]['message']['content']
        reply, emotion = parse_emotion(raw)
        update_affection(s, msg, reply)
        s["messages"].append({"role": "assistant", "content": reply})

        # 更新随机事件计数
        s["msg_count_since_event"] = s.get("msg_count_since_event", 0) + 1

        try: save_game(sid, "auto")
        except: pass

        # TTS 清理文本
        tts_text = clean_for_tts(reply)

        return jsonify({
            "reply": reply, "emotion": emotion,
            "affection": s["affection"], "scene": s["scene"],
            "events": s.get("triggered_events", []),
            "tts_text": tts_text,
        })
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI 响应超时"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/random_event', methods=['POST'])
def random_event():
    """该隐的随机主动互动"""
    data = request.json
    sid = data.get('session_id', 'default')
    s = get_session(sid)
    scene = s["scene"]
    
    event = get_random_event(scene, s["affection"])
    
    # 加入对话历史
    s["messages"].append({"role": "assistant", "content": event["text"]})
    s["msg_count_since_event"] = 0
    
    tts_text = clean_for_tts(event["text"])
    
    return jsonify({
        "text": event["text"],
        "emotion": event["emotion"],
        "tts_text": tts_text,
        "affection": s["affection"],
    })

@app.route('/api/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text', '').strip()
    if not text: return jsonify({"error": "空文本"}), 400
    
    # 使用已清理的文本，或自行清理
    text = clean_for_tts(text) if not data.get('pre_cleaned') else text
    text = text[:300]  # 限制长度避免超时
    
    if not text: return jsonify({"error": "清理后文本为空"}), 400

    try:
        payload = {"text": text, "format": "mp3", "mp3_bitrate": 64}
        if FISH_VOICE_MODEL_ID: payload["reference_id"] = FISH_VOICE_MODEL_ID
        r = requests.post(FISH_AUDIO_TTS_URL,
            headers={"Authorization": f"Bearer {FISH_AUDIO_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=20)
        if r.status_code != 200:
            return jsonify({"error": f"TTS {r.status_code}"}), 502
        return send_file(io.BytesIO(r.content), mimetype='audio/mpeg')
    except Exception as e:
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
    for f in os.listdir(SAVE_DIR):
        if f.startswith(sid) and f.endswith('.json'):
            with open(os.path.join(SAVE_DIR, f), 'r') as fh:
                d = json.load(fh)
                saves.append({"slot": d.get("slot",""), "timestamp": d["timestamp"],
                              "affection": d["affection"], "scene": d["scene"]})
    return jsonify({"saves": sorted(saves, key=lambda x: x["timestamp"], reverse=True)})

if __name__ == '__main__':
    print("🌙 月光罅隙 v3 | http://localhost:%d" % PORT)
    app.run(host='0.0.0.0', port=PORT, debug=os.environ.get("DEBUG","1")=="1")
