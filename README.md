# 🌙 月光别墅 - Moonlight Villa v2

AI 驱动的乙女向互动视觉小说

---

## 本地运行

```bash
cd moonlight-villa
pip install -r requirements.txt
python server.py
# 浏览器打开 http://localhost:5000
```

---

## 部署到云端（随时随地用）

### 推荐方案 ① — Render.com（免费）

最简单，适合个人使用，免费套餐够用。

**步骤：**

1. 注册 [render.com](https://render.com)（GitHub 登录即可）
2. 把项目上传到 GitHub 仓库（私有即可）
3. Render 控制台 → **New** → **Web Service**
4. 连接你的 GitHub 仓库
5. 设置：
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 60`
6. 添加环境变量（Settings → Environment）：
   ```
   DEEPSEEK_API_KEY = sk-624fe07b825945278cd4db6a51b08b0f
   FISH_AUDIO_API_KEY = ace09915a295439b80399d494f385231
   FISH_VOICE_MODEL_ID = （可选，填你选择的声音ID）
   DEBUG = 0
   ```
7. 点 Deploy，等几分钟就能拿到一个 `https://xxx.onrender.com` 的地址

> ⚠️ 免费版 15 分钟无访问会休眠，首次访问要等 ~30 秒唤醒。可付 $7/月去掉这个限制。

---

### 方案 ② — Railway.app（$5 免费额度/月）

速度比 Render 快，不会休眠。

1. 注册 [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. 自动检测 Python + Procfile
4. Variables 里填入 API keys
5. 自动分配域名 `xxx.up.railway.app`

---

### 方案 ③ — Fly.io（免费 3 个小机器）

性能最好，全球节点。

1. 安装 flyctl: `curl -L https://fly.io/install.sh | sh`
2. `fly auth login`
3. 在项目目录执行 `fly launch`
4. 设置 secrets:
   ```bash
   fly secrets set DEEPSEEK_API_KEY=sk-xxx FISH_AUDIO_API_KEY=ace-xxx
   ```
5. `fly deploy`

---

### 方案 ④ — 自己的 VPS

如果你有服务器（比如腾讯云/阿里云轻量），直接：

```bash
# 在服务器上
git clone 你的仓库
cd moonlight-villa
pip install -r requirements.txt

# 后台运行
nohup gunicorn server:app --bind 0.0.0.0:5000 --timeout 60 &

# 然后用 nginx 反代到 80/443 端口（可选配 HTTPS）
```

---

## 安全提醒

> 部署前建议把 API key 从代码中移除，只通过环境变量设置。
> 当前 server.py 已支持环境变量读取（`os.environ.get`），
> 只需删除默认值并在平台上配置即可。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| AI 实时对话 | DeepSeek 大模型扮演 Cain |
| 情绪系统 | 12 种情绪，影响立绘和氛围 |
| 好感度 | 0-100，影响角色态度和剧情 |
| 剧情事件 | 好感度触发的隐藏剧情线索 |
| 5 个场景 | 花园/藏书阁/舞厅/阁楼/酒窖 |
| 语音合成 | Fish Audio TTS 为角色配音 |
| 环境音效 | Web Audio API 生成场景氛围 |
| 存档系统 | 3 个手动存档位 + 自动存档 |
| 打字机效果 | 可调速，点击跳过 |
| 开场动画 | 沉浸式开场序幕 |
| 移动适配 | 安全区域/动态视口/触控优化 |

## 项目结构

```
moonlight-villa/
├── server.py          # 后端（Flask）
├── requirements.txt
├── Procfile           # 云部署启动配置
├── README.md
├── saves/             # 存档目录（自动创建）
└── static/
    ├── index.html     # 前端（React SPA）
    └── cain.jpg       # 角色立绘
```
