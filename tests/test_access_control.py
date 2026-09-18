import os
import tempfile
import unittest
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor
os.environ.setdefault('DEEPSEEK_API_KEY','test-only-key')
import server
from access_control import QuotaExceeded

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        server.GUARD.path=self.tmp.name+'/limits.sqlite3'
        server.app.config['TESTING']=True
        server.sessions.clear()
        self.client=server.app.test_client()
        self.db=patch.object(server,'sb',return_value=[{'id':'alice','passcode':'1234'}]).start()
        patch.object(server,'supabase_enabled',return_value=True).start()
        self.http=patch.object(server.http_req,'post').start()
        self.http.return_value=Mock(status_code=200,json=lambda:{'choices':[{'message':{'content':'先看看日晷。'}}]})
        patch.object(server,'save_game',return_value={}).start()
        patch.object(server,'save_game_db',return_value={}).start()
    def tearDown(self):
        patch.stopall();self.tmp.cleanup()
    def post(self,path,body=None,client=None):
        return (client or self.client).post('/api/'+path,json=body or {},base_url='https://localhost')
    def login(self):
        r=self.post('auth',{'name':'小贝','passcode':'1234'})
        self.assertEqual(r.status_code,200)
        self.assertIn('HttpOnly',r.headers['Set-Cookie'])
        self.assertIn('Secure',r.headers['Set-Cookie'])
        return self.post('session').json['session_id']
    def test_anonymous_cannot_spend_or_read(self):
        for route in ('chat','tts','load','save','session','saves/list','random_event','scene'):
            self.assertEqual(self.post(route,{'message':'hi','text':'hi'}).status_code,401)
        self.http.assert_not_called();self.db.assert_not_called()
    def test_auth_outage_never_registers(self):
        self.db.return_value=None
        self.assertEqual(self.post('auth',{'name':'x','passcode':'1234'}).status_code,503)
        self.assertEqual(self.db.call_count,1)
    def test_wrong_password_and_tampered_cookie(self):
        self.assertEqual(self.post('auth',{'name':'x','passcode':'0000'}).status_code,401)
        self.client.set_cookie('moonlight_auth','forged')
        self.assertEqual(self.post('me').status_code,401)
    def test_ownership_and_traversal(self):
        sid=self.login()
        self.assertEqual(self.post('load',{'session_id':sid,'player_id':'bob'}).status_code,403)
        server.sessions[sid]['owner_id']='bob'
        self.assertEqual(self.post('chat',{'session_id':sid,'message':'hello'}).status_code,403)
        server.sessions[sid]['owner_id']='alice'
        self.assertEqual(self.post('save',{'session_id':sid,'slot':'../../escape'}).status_code,400)
        self.http.assert_not_called()
    def test_old_save_access_and_logout(self):
        sid=self.login()
        with patch.object(server,'load_game_db',return_value={'messages':[{'role':'assistant','content':'旧对话'}],'affection':30,'scene':'garden'}):
            r=self.post('load',{'session_id':sid,'slot':'auto'})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json['affection'],30)
        self.assertEqual(self.post('logout').status_code,200)
        self.assertEqual(self.post('me').status_code,401)
    def test_input_and_csrf(self):
        sid=self.login()
        self.assertEqual(self.post('chat',{'session_id':sid,'message':'x'*501}).status_code,400)
        self.assertEqual(self.post('tts',{'text':['bad']}).status_code,400)
        self.assertEqual(self.post('chat',{'session_id':sid,'message':'x'*9000}).status_code,413)
        r=self.client.post('/api/tts',json={'text':'hi'},headers={'Origin':'https://evil.example'},base_url='https://localhost')
        self.assertEqual(r.status_code,403);self.http.assert_not_called()
    def test_chat_minute_limit_and_success(self):
        sid=self.login()
        for _ in range(6):
            self.assertEqual(self.post('chat',{'session_id':sid,'message':'你好'}).status_code,200)
        self.assertEqual(self.post('chat',{'session_id':sid,'message':'你好'}).status_code,429)
        self.assertEqual(self.http.call_count,6)
        self.assertEqual(self.http.call_args.kwargs['json']['model'],server.DEEPSEEK_MODEL)
    def test_quota_retry_and_rollback(self):
        sid=self.login();before=list(server.sessions[sid]['messages'])
        self.http.side_effect=server.http_req.exceptions.Timeout()
        with patch.dict(os.environ,{'LLM_DAILY_LIMIT':'1'}):
            r=self.post('chat',{'session_id':sid,'message':'hi'})
        self.assertEqual(r.status_code,429)
        self.assertEqual(self.http.call_count,1)
        self.assertEqual(server.sessions[sid]['messages'],before)
    def test_global_budget_across_accounts_and_concurrency(self):
        def charge(_):
            try: server.GUARD.count('testglobal',5);return 1
            except QuotaExceeded:return 0
        # Initialize schema before concurrent transactions.
        server.GUARD.count('init',1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(charge,range(20))),5)
    def test_tts_global_limit(self):
        self.login()
        with patch.object(server,'VOLC_TTS_TOKEN','test'),patch.dict(os.environ,{'TTS_DAILY_LIMIT':'0'}):
            self.assertEqual(self.post('tts',{'text':'你好'}).status_code,429)
        self.http.assert_not_called()

if __name__=='__main__': unittest.main()
