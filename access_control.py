"""Single-instance access control. SQLite counters survive worker restarts."""
import hashlib
import os
import sqlite3
import time
from urllib.parse import urlsplit
from flask import request, jsonify, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

class QuotaExceeded(Exception):
    pass

class Guard:
    def __init__(self, app, secret, sessions):
        self.sessions = sessions
        self.signer = URLSafeTimedSerializer(secret, salt='moonlight-auth-v1')
        self.path = os.environ.get('SECURITY_DB_PATH', 'security.sqlite3')
        app.config['MAX_CONTENT_LENGTH'] = 8192
        app.before_request(self.before)
        app.after_request(self.after)
        app.register_error_handler(QuotaExceeded, lambda e: (jsonify(error=str(e)), 429))
        app.register_error_handler(413, lambda e: (jsonify(error='请求过大，请缩短内容'), 413))

    def count(self, key, limit, window=86400):
        # Daily windows reset at midnight China Standard Time.
        now = int(time.time())
        bucket = (now + (28800 if window == 86400 else 0)) // window
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute('CREATE TABLE IF NOT EXISTS counters (k TEXT, b INTEGER, n INTEGER, expires INTEGER, PRIMARY KEY(k,b))')
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM counters WHERE expires < ?', (now,))
            row = db.execute('SELECT n FROM counters WHERE k=? AND b=?', (key,bucket)).fetchone()
            if (row[0] if row else 0) >= limit:
                raise QuotaExceeded('调用次数已达上限，请稍后或明日再试')
            db.execute('INSERT INTO counters VALUES(?,?,1,?) ON CONFLICT(k,b) DO UPDATE SET n=n+1', (key,bucket,now+window*2))

    def paid(self, kind):
        self.count('upstream:'+kind, int(os.environ.get('LLM_DAILY_LIMIT' if kind=='llm' else 'TTS_DAILY_LIMIT', '500' if kind=='llm' else '200')))

    def before(self):
        if not request.path.startswith('/api/'):
            return
        if request.method != 'POST':
            return jsonify(error='请使用 POST 请求'),405
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='不允许跨站请求'),403
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error='不允许跨站请求'),403
        data=request.get_json(silent=True)
        if not isinstance(data,dict):
            return jsonify(error='请求须为 JSON 对象'),400
        g.request_id = os.urandom(8).hex()
        if request.path == '/api/auth':
            # Do not trust client-supplied forwarding headers for rate limits.
            peer=hashlib.sha256((request.remote_addr or 'unknown').encode()).hexdigest()
            self.count('login-peer:'+peer,30,60)
            name=data.get('name','')
            if isinstance(name,str):
                self.count('login-name:'+hashlib.sha256(name.strip().encode()).hexdigest(),20)
            return
        try:
            g.identity=self.signer.loads(request.cookies.get('moonlight_auth',''),max_age=86400*7)
            if not isinstance(g.identity,dict) or not g.identity.get('player_id'):
                raise BadSignature('identity')
        except (BadSignature,SignatureExpired):
            return jsonify(error='登录已失效，请重新输入旅人名和暗号'),401
        pid=g.identity['player_id']
        if data.get('player_id') not in (None,pid):
            return jsonify(error='不能访问其他账户的存档'),403
        data['player_id']=pid
        if request.path in ('/api/chat','/api/scene','/api/random_event','/api/save','/api/load','/api/saves/list'):
            sid=data.get('session_id')
            if not isinstance(sid,str) or sid not in self.sessions:
                return jsonify(error='游戏会话已过期，请刷新后读档'),409
            if self.sessions[sid].get('owner_id') != pid:
                return jsonify(error='不能访问其他账户的会话'),403
        if request.path in ('/api/save','/api/load') and data.get('slot','manual') not in ('auto','manual','slot_1','slot_2','slot_3'):
            return jsonify(error='无效存档位'),400
        field={'/api/chat':'message','/api/tts':'text'}.get(request.path)
        if field:
            value=data.get(field)
            if not isinstance(value,str) or not value.strip() or len(value)>500:
                return jsonify(error='内容须为 1—500 字'),400
            kind='chat' if field=='message' else 'tts'
            self.count(kind+':minute:'+pid,6 if kind=='chat' else 12,60)
            self.count(kind+':day:'+pid,100)
        else:
            self.count('api:'+pid,60,60)

    def after(self, response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
            if response.status_code==429:
                response.headers['Retry-After']='60'
            # No prompts, keys, names or raw IP addresses in logs.
            pid=getattr(g,'identity',{}).get('player_id','anonymous')
            actor=hashlib.sha256(pid.encode()).hexdigest()[:12]
            print(f'[Access] id={getattr(g,"request_id","-")} actor={actor} path={request.path} status={response.status_code}',flush=True)
        return response

    def login_response(self,pid,name):
        response=jsonify(player_id=pid,name=name)
        response.set_cookie('moonlight_auth',self.signer.dumps(dict(player_id=pid,name=name)),httponly=True,secure=True,samesite='Strict',max_age=86400*7)
        return response
