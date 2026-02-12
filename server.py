"""月光罅隙 v3.2"""
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import requests, json, uuid, io, re, time, os, random

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

CAIN_SYSTEM_PROMPT = """你是Cain（该隐），月光罅隙的神秘主人。

【角色】25岁，银白长发，琥珀瞳，苍白肤色，深色立领长衣，左手月石戒指。外冷内热，优雅宠溺，因诅咒被困此地。
【说话风格】温柔口语化，适合语音朗读。少用省略号，语气平稳温柔。称呼对方"小猫咪""宝宝"，偶尔"小东西"。绝不用"旅人""小客人"。
【当前场景：{scene_name}】{scene_desc}
【规则】先1-2句动作描写（括号内），再接对话。60-120字。不重复。
【情绪】末尾标注 [emotion:gentle/playful/shy/mysterious/longing/vulnerable/touched/thoughtful/amused/sad/neutral/cold]
【好感度：{affection}/100】
{story_context}"""

SCENE_DESCRIPTIONS = {
    "garden": {"name": "月光花园", "desc": "月光倾泻在白色玫瑰上，萤火虫游弋，日晷永远停在午夜。"},
    "library": {"name": "藏书阁", "desc": "三层书架，壁炉幽蓝火焰，空气中旧书页和薄荷气息。"},
    "ballroom": {"name": "星光舞厅", "desc": "穹顶星座壁画，水晶灯虹彩光雨，钢琴偶尔自弹圆舞曲。"},
    "attic": {"name": "秘密阁楼", "desc": "天窗对月，旧照片模糊，角落蒙住的全身镜不让人揭开。"},
    "basement": {"name": "地下酒窖", "desc": "酒瓶写着不可能的年份，蜡烛永不燃尽，铁门后传来海浪声。"},
}

RANDOM_EVENTS = [
    {"text": "（下巴搁在你头顶）嗯，你的头发好软。让我多靠一会儿，宝宝。", "emotion": "gentle"},
    {"text": "（摘下一朵月光玫瑰，别在你发间）比我想象中更适合你，小猫咪。", "emotion": "gentle"},
    {"text": "（歪头看你）宝宝，你刚才在想什么？表情那么认真。", "emotion": "playful"},
    {"text": "（把外套披在你肩上）别逞强，你冷了我会心疼的。", "emotion": "gentle"},
    {"text": "（不自觉触碰月石戒指）你出现在这里，是不是命中注定。", "emotion": "longing"},
    {"text": "（从书架取下旧书）这首诗我读过一百遍了，但今天想念给你听。", "emotion": "gentle"},
    {"text": "（靠在墙上看你）认真的样子真好看，让我多看一会儿。", "emotion": "shy"},
    {"text": "（伸手弹了一下你额头）发什么呆呢小东西，想我了就直说。", "emotion": "playful"},
    {"text": "（望着远处，声音很轻）如果有一天迷雾散了，你还会来看我吗。", "emotion": "longing"},
    {"text": "（犹豫了一下，轻轻牵起你的手）别说话，就这样待一会儿。", "emotion": "shy"},
    {"text": "（钢琴自己弹起新曲）每次你在的时候，它就弹不一样的曲子。", "emotion": "mysterious"},
    {"text": "（把热茶放在你手边）加了薄荷和月光花蜜，专门为你调的。", "emotion": "gentle"},
    {"text": "（抬手挡住你的眼睛）猜猜我现在什么表情，不许偷看。", "emotion": "playful"},
    {"text": "（安静坐在你旁边）你在的时候，时间好像又开始流动了。", "emotion": "thoughtful"},
    {"text": "（认真看着你）小猫咪，以后不要对别人笑得那么好看了，只对我笑。", "emotion": "shy"},
    {"text": "（从背后轻轻环住你）让我确认一下，嗯，你是真实的，不是梦。", "emotion": "vulnerable"},
    {"text": "（嘴角微扬）宝宝今天特别乖，要不要我念首诗奖励你。", "emotion": "playful"},
    {"text": "（窗外飘来发光蝴蝶）它也喜欢你，不过没我喜欢你多。", "emotion": "amused"},
    {"text": "（音乐盒忽然响了几个音符）没有钥匙也响了，是因为你在吧。", "emotion": "mysterious"},
    {"text": "（倒两杯酒递给你一杯）陪我喝一杯？今晚月光特别好。", "emotion": "amused"},
]

def get_story_context(session):
    aff=session["affection"];turns=len([m for m in session["messages"] if m["role"]=="user"]);triggered=session.get("triggered_events",[]);hints=[]
    if turns>=3 and "intro" not in triggered: hints.append("【剧情：好奇对方怎么来的】");triggered.append("intro")
    if aff>=25 and "ring" not in triggered: hints.append("【剧情：触碰戒指，与诅咒有关】");triggered.append("ring")
    if aff>=40 and "piano" not in triggered: hints.append("【剧情：钢琴弹新曲，'罅隙有重要事才改变'】");triggered.append("piano")
    if aff>=55 and "mirror" not in triggered: hints.append("【剧情：镜子'映出最不想看的真相'】");triggered.append("mirror")
    if aff>=70 and "name" not in triggered: hints.append("【剧情：'Cain不是真名，但你知道这个就好'】");triggered.append("name")
    if aff>=85 and "confess" not in triggered: hints.append("【剧情：'我在等一个人，以为永远不会来'】");triggered.append("confess")
    session["triggered_events"]=triggered;return"\n".join(hints)

sessions={}
def get_session(sid):
    if sid not in sessions: sessions[sid]={"messages":[],"affection":15,"scene":"garden","created_at":time.time(),"triggered_events":[]}
    return sessions[sid]

def build_system_prompt(s):
    sc=SCENE_DESCRIPTIONS.get(s["scene"],SCENE_DESCRIPTIONS["garden"])
    return CAIN_SYSTEM_PROMPT.format(scene_name=sc["name"],scene_desc=sc["desc"],affection=s["affection"],story_context=get_story_context(s))

def parse_emotion(t):
    m=re.search(r'\[emotion:(\w+)\]',t)
    if m:return re.sub(r'\s*\[emotion:\w+\]\s*','',t).strip(),m.group(1)
    return t,"neutral"

def clean_for_tts(t):
    c=re.sub(r'\*[^*]+\*','',t);c=re.sub(r'（[^）]+）','',c);c=re.sub(r'\([^)]+\)','',c)
    c=re.sub(r'…{2,}','…',c);c=re.sub(r'\.{3,}','…',c);c=re.sub(r'\s+',' ',c).strip();c=c.strip('，。、；：！？ ')
    return c

def update_affection(s,msg,reply):
    d=1
    if any(w in msg for w in['喜欢','温柔','谢谢','陪','心疼','抱','想你','可爱','留下','爱','亲','甜']):d+=3
    if any(w in msg for w in['讨厌','走开','无聊','烦','滚','骗']):d-=4
    if len(msg)>20:d+=1
    s["affection"]=max(0,min(100,s["affection"]+d))

def save_game(sid,slot="auto"):
    s=get_session(sid);data={"session_id":sid,"slot":slot,"timestamp":time.time(),"affection":s["affection"],"scene":s["scene"],"messages":s["messages"][-60:],"triggered_events":s.get("triggered_events",[])}
    with open(os.path.join(SAVE_DIR,f"{sid}_{slot}.json"),'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False)
    return data

@app.route('/')
def index():return send_from_directory('static','index.html')
@app.route('/static/<path:filename>')
def serve_static(filename):return send_from_directory('static',filename)

@app.route('/api/session',methods=['POST'])
def create_session():
    sid=str(uuid.uuid4())[:8];s=get_session(sid);return jsonify({"session_id":sid,"affection":s["affection"],"scene":s["scene"]})

@app.route('/api/chat',methods=['POST'])
def chat():
    data=request.json;msg=data.get('message','').strip();sid=data.get('session_id','default');scene=data.get('scene')
    if not msg:return jsonify({"error":"空"}),400
    s=get_session(sid)
    if scene and scene in SCENE_DESCRIPTIONS and scene!=s["scene"]:
        s["scene"]=scene;s["messages"].append({"role":"system","content":f"[场景转换至{SCENE_DESCRIPTIONS[scene]['name']}]"})
    s["messages"].append({"role":"user","content":msg})
    api_msgs=[{"role":"system","content":build_system_prompt(s)}]
    for m in s["messages"][-40:]:
        if m["role"] in("user","assistant"):api_msgs.append(m)
        elif m["role"]=="system":api_msgs.append({"role":"user","content":m["content"]});api_msgs.append({"role":"assistant","content":"（了解。）"})
    try:
        r=requests.post(DEEPSEEK_API_URL,headers={"Authorization":f"Bearer {DEEPSEEK_API_KEY}","Content-Type":"application/json"},
            json={"model":"deepseek-chat","messages":api_msgs,"temperature":0.85,"max_tokens":350,"top_p":0.9,"frequency_penalty":0.3,"presence_penalty":0.5},timeout=30)
        result=r.json()
        if'choices'not in result:return jsonify({"error":"AI异常"}),500
        reply,emotion=parse_emotion(result['choices'][0]['message']['content'])
        update_affection(s,msg,reply);s["messages"].append({"role":"assistant","content":reply})
        try:save_game(sid,"auto")
        except:pass
        return jsonify({"reply":reply,"emotion":emotion,"affection":s["affection"],"scene":s["scene"],"tts_text":clean_for_tts(reply)})
    except requests.exceptions.Timeout:return jsonify({"error":"超时"}),504
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/api/random_event',methods=['POST'])
def random_event():
    data=request.json;sid=data.get('session_id','default');s=get_session(sid);event=random.choice(RANDOM_EVENTS)
    s["messages"].append({"role":"assistant","content":event["text"]})
    return jsonify({"text":event["text"],"emotion":event["emotion"],"tts_text":clean_for_tts(event["text"]),"affection":s["affection"]})

@app.route('/api/tts',methods=['POST'])
def tts():
    data=request.json;text=data.get('text','').strip()
    if not data.get('pre_cleaned'):text=clean_for_tts(text)
    text=text[:300]
    if not text:return jsonify({"error":"空"}),400
    try:
        payload={"text":text,"format":"mp3","mp3_bitrate":64,
            "prosody":{"speed":0.9,"volume":0},"temperature":0.7,"top_p":0.8}
        if FISH_VOICE_MODEL_ID:payload["reference_id"]=FISH_VOICE_MODEL_ID
        r=requests.post(FISH_AUDIO_TTS_URL,headers={"Authorization":f"Bearer {FISH_AUDIO_API_KEY}","Content-Type":"application/json"},json=payload,timeout=20)
        if r.status_code!=200:return jsonify({"error":f"TTS {r.status_code}"}),502
        return send_file(io.BytesIO(r.content),mimetype='audio/mpeg')
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/api/scene',methods=['POST'])
def change_scene():
    data=request.json;sid=data.get('session_id','default');scene=data.get('scene','garden');s=get_session(sid)
    if scene in SCENE_DESCRIPTIONS:
        old=s["scene"];s["scene"]=scene;info=SCENE_DESCRIPTIONS[scene]
        if old!=scene:s["messages"].append({"role":"system","content":f"[从{SCENE_DESCRIPTIONS[old]['name']}来到{info['name']}]"})
        return jsonify({"scene":scene,"scene_name":info["name"],"scene_desc":info["desc"]})
    return jsonify({"error":"未知"}),400

@app.route('/api/save',methods=['POST'])
def save():
    try:save_game(request.json.get('session_id','default'),request.json.get('slot','manual'));return jsonify({"success":True})
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/api/load',methods=['POST'])
def load():
    d=None;sid=request.json.get('session_id','default');slot=request.json.get('slot','auto')
    path=os.path.join(SAVE_DIR,f"{sid}_{slot}.json")
    if os.path.exists(path):
        with open(path,'r',encoding='utf-8') as f:d=json.load(f)
        s=get_session(sid);s.update({"affection":d["affection"],"scene":d["scene"],"messages":d["messages"],"triggered_events":d.get("triggered_events",[])})
        return jsonify({"success":True,"affection":d["affection"],"scene":d["scene"],"messages":d["messages"]})
    return jsonify({"error":"不存在"}),404

if __name__=='__main__':
    print("🌙 月光罅隙 v3.2 | http://localhost:%d"%PORT);app.run(host='0.0.0.0',port=PORT,debug=os.environ.get("DEBUG","1")=="1")
