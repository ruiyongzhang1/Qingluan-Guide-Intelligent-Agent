# 青鸾向导 - AI智能助手系统

一个基于Flask和LangChain的智能AI助手系统，支持多智能体对话、旅行规划和历史记录管理。

## 🌟 功能特性

### 🤖 智能对话
- **多智能体支持**: 通用AI助手和专门的旅行规划智能体
- **流式响应**: 实时显示AI回复，提供更好的用户体验
- **Markdown渲染**: 支持代码高亮、表格、列表等富文本格式
- **上下文记忆**: 保持对话连续性，支持多轮对话

### ✈️ 旅行规划
- **智能规划**: 基于用户需求自动生成旅行方案
- **多信息源**: 集成航班、酒店、景点、餐厅等搜索功能
- **预算控制**: 根据用户预算提供个性化推荐
- **详细方案**: 包含行程安排、交通规划、餐饮推荐等

### 💾 数据管理
- **SQLite数据库**: 高效的数据存储和查询
- **用户系统**: 注册登录、会话管理
- **历史记录**: 完整的对话历史保存和检索
- **数据安全**: 用户权限验证和数据隔离

## 🚀 快速开始

### 环境要求
- Python 3.8+
- SQLite3
- Redis (可选，用于缓存)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd new_py
```

2. **创建虚拟环境**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```


4. **配置环境变量**
创建 `.env` 文件：
```env
FLASK_SECRET_KEY=your_secret_key_here
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_URL=https://api.openai.com/v1
SEARCHAPI_API_KEY=your_searchapi_key
```

5. **初始化数据库**(初始化十分重要！！！)
```bash
python database_self.py
```

6. **运行应用**
```bash
python app.py
```

7. **访问应用**
打开浏览器访问 `http://localhost:5000`

## 📁 项目结构

```
new_py/
├── app.py                 # Flask主应用
├── ai_agent.py           # AI智能体核心逻辑
├── database_self.py      # 数据库操作模块
├── db_manager.py         # 数据库管理工具（运行该脚本可以查看数据库具体信息）
├── app.db               # SQLite数据库文件
├── templates/           # HTML模板
│   ├── index.html       # 首页
│   ├── login.html       # 登录页面
│   ├── chat.html        # 聊天界面
│   └── travel.html      # 旅行规划界面
├── static/              # 静态资源
│   ├── style.css        # 主样式文件
│   ├── chat.css         # 聊天界面样式
│   ├── script.js        # 聊天和登录JavaScript
│   └── travel.js        # 旅行规划JavaScript
└── redis/               # Redis相关文件 (智能体记忆使用redis尚未实现)
```

## 🔧 核心模块

### AI智能体系统 (`ai_agent.py`)
- **多智能体架构**: 支持不同类型的AI助手
- **流式响应**: 实时生成和显示AI回复
- **旅行规划**: 专门的旅行规划智能体
- **搜索集成**: 集成外部搜索API获取实时信息

### 数据库系统 (`database_self.py`)
- **用户管理**: 用户注册、登录、验证
- **对话存储**: 完整的对话历史记录
- **数据安全**: 用户权限验证和数据隔离
- **性能优化**: 索引优化和查询优化

### Web界面
- **响应式设计**: 适配不同设备屏幕
- **实时交互**: WebSocket和SSE支持
- **代码高亮**: 支持多种编程语言语法高亮
- **Markdown渲染**: 完整的Markdown支持

## 🎯 使用指南

### 用户注册和登录
1. 访问首页，点击"登录/注册"
2. 输入邮箱和密码进行注册
3. 登录后即可开始使用AI助手

### 智能对话
1. 在聊天界面输入问题
2. AI会实时生成回复
3. 支持代码、表格、列表等富文本格式
4. 可以查看和恢复历史对话

### 旅行规划
1. 点击"旅行规划"进入专门界面
2. 填写旅行需求（目的地、时间、预算等）
3. AI会生成详细的旅行方案
4. 包含航班、酒店、景点、餐饮等推荐

### 历史记录管理
1. 点击"历史对话"查看所有对话
2. 可以点击任意对话恢复
3. 支持删除单个对话或清空所有历史
4. 数据安全存储在SQLite数据库中

## 🛠️ 开发工具

### 数据库管理工具
```bash
# 启动GUI管理工具
python db_manager.py
```

功能包括：
- 查看数据库表结构
- 管理用户数据
- 查看对话和消息
- 数据库统计信息
- 删除用户或对话

### 命令行工具
```bash
# 查看数据库统计
python -c "from database_self import db; print(db.get_user_stats('user@example.com'))"

# 删除特定对话
python -c "from database_self import db; db.delete_conversation('conversation_id')"
```

## 🔒 安全特性

- **用户认证**: 基于session的用户认证系统
- **数据隔离**: 用户只能访问自己的数据
- **SQL注入防护**: 使用参数化查询
- **XSS防护**: 输入验证和输出转义
- **CSRF防护**: 表单令牌验证

## 📊 性能优化

- **数据库索引**: 优化查询性能
- **连接池**: 数据库连接复用
- **缓存机制**: Redis缓存支持
- **流式响应**: 减少内存占用
- **异步处理**: 非阻塞I/O操作

## 🚀 部署指南

### 开发环境
```bash
python app.py
```

## 🔧 配置选项

### 环境变量
- `FLASK_SECRET_KEY`: Flask会话密钥
- `OPENAI_API_KEY`: OpenAI API密钥
- `OPENAI_API_URL`: OpenAI API地址
- `SEARCHAPI_API_KEY`: 搜索API密钥

### 数据库配置
- 数据库文件: `app.db`
- 自动创建表结构
- 支持外键约束
- 自动索引优化


## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情


## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [LangChain](https://langchain.com/) - AI应用框架
- [OpenAI](https://openai.com/) - AI模型服务
- [SQLite](https://www.sqlite.org/) - 数据库引擎

---

**青鸾向导** - 让AI助手更智能，让对话更有趣！ 🚀
