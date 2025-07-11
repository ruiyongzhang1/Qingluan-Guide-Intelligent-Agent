# AI智能体Redis记忆系统使用说明

## 🧠 概述

本系统为AI智能体提供了基于Redis的持久化记忆功能，支持：
- **对话历史持久化**：即使重启应用，对话记忆也不会丢失
- **多用户隔离**：每个用户的对话记忆完全独立
- **智能过期清理**：自动清理7天前的旧记忆
- **优雅降级**：Redis不可用时自动回退到内存模式

## 🚀 快速开始

### 1. 启动Redis服务器

**方法一：使用启动脚本（推荐）**
```bash
python start_redis.py
```

**方法二：手动启动（Windows）**
```bash
# 进入redis目录
cd redis
# 启动Redis服务器
redis-server.exe redis.windows.conf
```

**方法三：Linux/Mac系统**
```bash
# 如果已安装Redis
redis-server

# 如果未安装，先安装
# Ubuntu/Debian:
sudo apt-get install redis-server
# macOS:
brew install redis
```

### 2. 启动应用
```bash
python app.py
```

### 3. 验证记忆功能

1. **登录应用**并开始对话
2. **测试记忆**：
   - 发送：`"我叫张三"`
   - 然后发送：`"你还记得我的名字吗？"`
   - AI应该能记住你的名字

3. **测试持久化**：
   - 重启应用
   - 继续之前的对话
   - 记忆应该仍然存在

## 📊 记忆系统监控

### 查看记忆统计
访问：`http://localhost:5000/memory_stats`

返回信息包括：
```json
{
  "status": "success",
  "stats": {
    "redis_available": true,
    "using_redis": true,
    "active_sessions": 5,
    "max_memory_length": 60,
    "memory_ttl_hours": 168.0,
    "key_prefix": "agent_memory:",
    "active_agent_sessions": 3
  }
}
```

### 统计信息说明
- `redis_available`: Redis库是否可用
- `using_redis`: 是否正在使用Redis（false表示回退到内存模式）
- `active_sessions`: Redis中的活跃会话数
- `max_memory_length`: 每个会话最大记忆条数（60条）
- `memory_ttl_hours`: 记忆过期时间（168小时=7天）
- `active_agent_sessions`: 当前活跃的智能体会话数

## ⚙️ 高级配置

### 自定义Redis配置
在代码中修改Redis连接参数：

```python
# 在app.py或其他地方初始化AgentService时
redis_config = {
    'redis_host': 'localhost',      # Redis服务器地址
    'redis_port': 6379,             # Redis端口
    'redis_db': 0,                  # Redis数据库编号
    'redis_password': None,         # Redis密码
    'max_memory_length': 60,        # 最大记忆条数
    'memory_ttl': 7*24*3600,       # 过期时间（秒）
    'key_prefix': 'agent_memory:'   # 键前缀
}

agent_service = get_agent_service(redis_config=redis_config)
```

### 环境变量配置
可以通过环境变量配置Redis：

```bash
# .env文件
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
REDIS_DB=0
```

## 🔧 故障排除

### 常见问题

**1. Redis连接失败**
```
❌ Redis连接失败: [Errno 111] Connection refused
```
**解决方案**：
- 确保Redis服务器正在运行
- 检查Redis地址和端口配置
- 运行 `python start_redis.py`

**2. Redis包未安装**
```
警告: redis包未安装，将使用内存模式
```
**解决方案**：
```bash
pip install redis==5.0.1
```

**3. 记忆不持久化**
检查日志中是否显示：
```
⚠️  使用内存模式（不持久化）
```
这表示Redis不可用，系统回退到内存模式

### 调试技巧

**1. 检查Redis状态**
```bash
python start_redis.py
```

**2. 使用Redis CLI检查数据**
```bash
# 连接Redis
redis-cli

# 查看所有键
keys agent_memory:*

# 查看特定键的内容
lrange agent_memory:user@email.com_conv123 0 -1

# 查看键的过期时间
ttl agent_memory:user@email.com_conv123
```

**3. 查看应用日志**
启动应用时观察输出：
```
✅ Redis记忆存储已连接: localhost:6379
初始化 AgentService...
AgentService 初始化完成（使用懒加载模式 + Redis记忆）
```

## 🗂️ 数据结构

### Redis键命名规则
```
agent_memory:{user_email}_{conv_id}
```

示例：
```
agent_memory:user@example.com_12345678-1234-1234-1234-123456789abc
```

### 消息格式
每条记忆消息的JSON格式：
```json
{
  "role": "user",           // 或 "assistant"
  "content": "消息内容",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🔒 安全考虑

1. **生产环境建议**：
   - 设置Redis密码
   - 限制Redis网络访问
   - 使用SSL连接

2. **隐私保护**：
   - 记忆自动7天过期
   - 用户登出时清理记忆
   - 数据完全隔离

## 📈 性能优化

1. **记忆长度控制**：
   - 默认每个会话最多60条记忆
   - 自动清理旧记忆避免内存溢出

2. **网络优化**：
   - 使用连接池
   - 设置合理的超时时间

3. **存储优化**：
   - JSON压缩存储
   - 自动过期清理

## 🚀 扩展功能

### 未来可能的增强：
- [ ] 记忆内容的语义搜索
- [ ] 记忆重要性评分
- [ ] 跨会话的用户画像记忆
- [ ] 记忆内容的加密存储
- [ ] 分布式Redis集群支持

---

如有问题或建议，请联系开发团队！🎉 