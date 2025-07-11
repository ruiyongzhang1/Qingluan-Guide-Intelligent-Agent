# 青鸾向导 (QL Guide) - 智能AI助手系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com)
[![Redis](https://img.shields.io/badge/Redis-5.0+-red.svg)](https://redis.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个功能强大的智能AI助手系统，基于多智能体架构，支持对话记忆、旅行规划、PDF生成等多种功能。

## 🌟 核心特性

### 🤖 多智能体系统
- **通用AI助手** (`NormalAgent`): 处理日常问答和通用任务
- **旅行规划师** (`PlannerAgent`): 专业的旅行方案制定
- **景点向导** (`AttractionGuide`): 详细的景点介绍和推荐
- **PDF生成器** (`PdfAgent`): 智能文档生成和格式化

### 🧠 Redis记忆系统
- **持久化记忆**: 基于Redis的对话上下文存储 (7天TTL)
- **多用户隔离**: 每用户独立的记忆空间
- **优雅降级**: Redis不可用时自动回退到内存模式
- **智能管理**: 最多保存60条历史消息，自动清理

### 💬 智能对话体验
- **流式响应**: 实时显示AI回复，提升用户体验
- **Markdown渲染**: 支持代码高亮、表格、列表等富文本
- **上下文连续性**: 记住对话历史，支持多轮深度交流
- **多种交互模式**: 文本对话、旅行规划、PDF生成

### 🗄️ 完整数据管理
- **SQLite数据库**: 高性能的本地数据存储
- **用户系统**: 安全的注册登录机制
- **历史记录**: 完整的对话历史保存和检索
- **数据安全**: 用户权限验证和数据隔离

## 🚀 快速开始

### 系统要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows / Linux / macOS
- **内存**: 建议 2GB 以上
- **存储**: 至少 500MB 可用空间

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd QL_guide
```

2. **创建虚拟环境**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
创建 `.env` 文件：
```env
# Flask配置
FLASK_SECRET_KEY=your_secret_key_here

# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_URL=https://api.openai.com/v1

# 搜索API配置
SEARCHAPI_API_KEY=your_searchapi_key

# Redis配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

5. **初始化数据库** ⚠️ 重要步骤！
```bash
python database_self.py
```

6. **启动Redis服务器**（推荐）
```bash
python start_redis.py
```

7. **运行应用**
```bash
python app.py
```

8. **访问应用**
打开浏览器访问: `http://localhost:5000`

## 📁 项目架构

```
QL_guide/
├── 📄 app.py                      # Flask主应用入口
├── 🗃️ app.db                      # SQLite数据库文件
├── 📋 requirements.txt            # Python依赖列表
├── 🚀 start_redis.py             # Redis启动脚本
├── 👁️ redis_viewer.py            # Redis数据查看工具
├── 🗄️ database_self.py           # 数据库初始化和操作
├── 🔧 db_manager.py              # 数据库管理GUI工具
│
├── 🤖 agent/                      # AI智能体核心模块
│   ├── ai_agent.py               # 多智能体管理器
│   ├── redis_memory.py           # Redis记忆存储
│   ├── pdf_generator.py          # PDF生成智能体
│   ├── attraction_guide.py       # 景点向导智能体
│   ├── prompts.py               # 智能体提示词模板
│   └── mcp_server.py            # MCP协议服务器
│
├── 🎨 templates/                  # HTML模板文件
│   ├── index.html               # 首页
│   ├── login.html               # 登录注册页面
│   ├── chat.html                # 聊天界面
│   └── travel.html              # 旅行规划界面
│
├── 🎭 static/                     # 静态资源文件
│   ├── style.css                # 主样式文件
│   ├── chat.css                 # 聊天界面样式
│   ├── travel.css               # 旅行界面样式
│   ├── script.js                # 主要JavaScript功能
│   ├── travel.js                # 旅行规划交互逻辑
│   └── *.jpg/png                # 图片资源
│
└── 📦 redis/                      # Redis服务器文件
    ├── dump.rdb                 # Redis数据快照
    ├── redis-server.exe         # Windows Redis服务器
    ├── redis-cli.exe            # Redis命令行工具
    └── *.conf                   # Redis配置文件
```

## 🎯 功能模块详解

### 🤖 多智能体系统

#### 1. 通用AI助手 (NormalAgent)
- **功能**: 处理日常问答、编程问题、知识查询
- **特点**: 上下文理解、代码生成、逻辑推理
- **使用场景**: 学习辅导、问题解答、创意写作

#### 2. 旅行规划师 (PlannerAgent)
- **功能**: 制定详细旅行方案
- **整合服务**: 航班查询、酒店预订、景点推荐
- **输出格式**: 结构化行程表、预算分析
- **使用场景**: 假期规划、商务出行、深度游

#### 3. 景点向导 (AttractionGuide)
- **功能**: 提供详细景点信息和推荐
- **数据来源**: 实时搜索API
- **特色**: 本地化推荐、实用攻略
- **使用场景**: 目的地探索、行程优化

#### 4. PDF生成器 (PdfAgent)
- **功能**: 智能文档生成和格式化
- **支持格式**: Markdown转PDF、富文本排版
- **特色**: 自动排版、样式美化
- **使用场景**: 报告生成、文档制作

### 🧠 记忆系统架构

#### 双层存储设计
```
📊 SQLite数据库 (长期存储)
├── 用户信息管理
├── 完整对话历史
└── 数据统计分析

🔄 Redis缓存 (工作记忆)
├── 活跃对话上下文 (60条)
├── 智能体状态管理
└── 7天自动过期
```

#### 记忆管理特性
- **上下文窗口**: 每个会话最多60条消息
- **自动清理**: 超出限制时智能清理最旧消息
- **用户隔离**: 完全独立的用户记忆空间
- **降级策略**: Redis不可用时无缝切换到内存模式

### 🌐 Web界面功能

#### 用户管理系统
- **注册登录**: 基于邮箱的安全认证
- **支持邮箱**: QQ、Gmail、Outlook、163、Foxmail
- **会话管理**: 安全的session机制
- **权限控制**: 用户数据完全隔离

#### 交互界面
- **响应式设计**: 适配手机、平板、电脑
- **实时对话**: 流式响应显示
- **历史管理**: 对话恢复、删除、清空
- **多模式切换**: 聊天/旅行规划一键切换

## 🔧 高级配置

### Redis配置优化
```python
# 自定义Redis配置
redis_config = {
    'redis_host': 'localhost',
    'redis_port': 6379,
    'redis_db': 0,
    'redis_password': None,
    'max_memory_length': 60,        # 记忆条数
    'memory_ttl': 7*24*3600,        # 7天过期
    'key_prefix': 'agent_memory:'
}
```

### 智能体参数调优
```python
# 在prompts.py中调整
AGENT_CONFIGS = {
    'temperature': 0.7,             # 创意度控制
    'max_tokens': 2000,             # 回复长度限制
    'context_window': 60,           # 上下文窗口
    'stream_chunk_size': 1024       # 流式响应块大小
}
```

## 🛠️ 开发和运维工具

### 数据库管理工具
```bash
# 启动GUI管理界面
python db_manager.py
```
功能包括：
- 📊 数据库统计和分析
- 👥 用户数据管理
- 💬 对话记录查看
- 🗑️ 数据清理工具

### Redis监控工具
```bash
# 查看Redis数据
python redis_viewer.py

# 记忆系统状态监控
curl http://localhost:5000/memory_stats
```

### 命令行工具
```bash
# 查看用户统计
python -c "from database_self import db; print(db.get_user_stats('user@example.com'))"

# 清理用户数据
python -c "from database_self import db; db.clear_user_history('user@example.com')"

# 删除特定对话
python -c "from database_self import db; db.delete_conversation('conversation_id')"
```

## 📊 性能优化策略

### 数据库优化
- **索引优化**: 针对查询模式建立合适索引
- **连接池**: 数据库连接复用机制
- **查询优化**: 参数化查询防止SQL注入
- **分页加载**: 大量历史记录分页显示

### Redis优化
- **内存管理**: 自动清理过期数据
- **连接复用**: 单例模式Redis连接
- **序列化优化**: JSON格式消息存储
- **网络优化**: 本地Redis部署减少延迟

### Web性能优化
- **流式响应**: 减少用户等待时间
- **静态资源**: CSS/JS文件压缩
- **异步处理**: 非阻塞I/O操作
- **缓存策略**: 浏览器和服务器端缓存

## 🔒 安全特性

### 用户认证安全
- **密码保护**: 安全的密码存储机制
- **会话管理**: 基于Flask Session的安全认证
- **权限验证**: 每个请求的用户权限检查
- **数据隔离**: 用户间数据完全隔离

### 数据安全
- **SQL注入防护**: 参数化查询
- **XSS防护**: 输入验证和输出转义
- **CSRF防护**: 表单令牌验证
- **敏感信息**: 环境变量存储API密钥

## 🚀 部署指南

### 开发环境部署
```bash
# 开发模式运行
python app.py
# 应用将在 http://localhost:5000 启动
```

### 生产环境部署
```bash
# 使用Gunicorn（推荐）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 使用uWSGI
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable app
```

### Docker部署
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🔧 故障排除

### 常见问题解决

#### 1. Redis连接失败
```
❌ 错误: Redis连接失败
✅ 解决: python start_redis.py
```

#### 2. 数据库未初始化
```
❌ 错误: no such table: users
✅ 解决: python database_self.py
```

#### 3. 依赖包缺失
```
❌ 错误: ModuleNotFoundError
✅ 解决: pip install -r requirements.txt
```

#### 4. API密钥未配置
```
❌ 错误: Invalid API Key
✅ 解决: 检查.env文件中的OPENAI_API_KEY
```

### 调试技巧
- 检查应用启动日志
- 使用 `redis_viewer.py` 查看Redis数据
- 使用 `db_manager.py` 检查数据库状态
- 访问 `/memory_stats` 查看系统状态

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -am '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建 Pull Request

### 代码规范
- 遵循 PEP8 Python代码规范
- 添加适当的注释和文档字符串
- 编写单元测试覆盖新功能
- 确保现有测试通过

## 📄 许可证

本项目采用 [MIT许可证](LICENSE) - 查看LICENSE文件了解详情

## 🙏 致谢

感谢以下开源项目的支持：

- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Redis](https://redis.io/) - 高性能内存数据库
- [OpenAI](https://openai.com/) - 先进的AI模型服务
- [SQLite](https://www.sqlite.org/) - 嵌入式数据库引擎
- [LangChain](https://langchain.com/) - AI应用开发框架

## 📞 联系方式

- **项目地址**: [GitHub Repository](https://github.com/your-username/QL_guide)
- **问题反馈**: [Issues页面](https://github.com/your-username/QL_guide/issues)
- **功能建议**: [Discussions](https://github.com/your-username/QL_guide/discussions)

---

**青鸾向导** - 让AI助手更智能，让对话更自然！ 🚀✨
