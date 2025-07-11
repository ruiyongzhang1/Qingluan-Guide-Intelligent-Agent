"""
Redis记忆管理模块
为AI智能体提供持久化的对话记忆存储
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("警告: redis包未安装，将使用内存模式")


class RedisMemory:
    """基于Redis的智能体记忆存储"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, 
                 redis_password=None, key_prefix='agent_memory:', 
                 max_memory_length=60, memory_ttl=7*24*3600):  # 7天过期
        """
        初始化Redis记忆存储
        
        Args:
            redis_host: Redis服务器地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码
            key_prefix: 内存键前缀
            max_memory_length: 最大记忆条数
            memory_ttl: 记忆过期时间（秒）
        """
        self.key_prefix = key_prefix
        self.max_memory_length = max_memory_length
        self.memory_ttl = memory_ttl
        
        # 初始化Redis连接
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,  # 自动解码响应为字符串
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试连接
                self.redis_client.ping()
                self.use_redis = True
                print(f"✅ Redis记忆存储已连接: {redis_host}:{redis_port}")
            except Exception as e:
                print(f"❌ Redis连接失败: {e}")
                self.use_redis = False
                self._fallback_memory = {}
        else:
            self.use_redis = False
            self._fallback_memory = {}
            print("⚠️  使用内存模式（不持久化）")
    
    def _get_memory_key(self, session_id: str) -> str:
        """生成记忆存储键"""
        return f"{self.key_prefix}{session_id}"
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        添加对话记录到记忆中
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
            
        Returns:
            bool: 是否成功添加
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.use_redis:
            return self._add_message_redis(session_id, message)
        else:
            return self._add_message_fallback(session_id, message)
    
    def _add_message_redis(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Redis模式添加消息"""
        try:
            key = self._get_memory_key(session_id)
            
            # 将消息添加到列表尾部
            self.redis_client.rpush(key, json.dumps(message, ensure_ascii=False))
            
            # 限制列表长度
            self.redis_client.ltrim(key, -self.max_memory_length, -1)
            
            # 设置过期时间
            self.redis_client.expire(key, self.memory_ttl)
            
            return True
        except Exception as e:
            print(f"Redis添加消息失败: {e}")
            return False
    
    def _add_message_fallback(self, session_id: str, message: Dict[str, Any]) -> bool:
        """内存模式添加消息"""
        if session_id not in self._fallback_memory:
            self._fallback_memory[session_id] = []
        
        self._fallback_memory[session_id].append(message)
        
        # 限制长度
        if len(self._fallback_memory[session_id]) > self.max_memory_length:
            self._fallback_memory[session_id] = self._fallback_memory[session_id][-self.max_memory_length:]
        
        return True
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取会话的记忆消息
        
        Args:
            session_id: 会话ID
            limit: 限制返回的消息数量
            
        Returns:
            List[Dict]: 消息列表
        """
        if self.use_redis:
            return self._get_messages_redis(session_id, limit)
        else:
            return self._get_messages_fallback(session_id, limit)
    
    def _get_messages_redis(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Redis模式获取消息"""
        try:
            key = self._get_memory_key(session_id)
            
            if limit:
                # 获取最后N条消息
                raw_messages = self.redis_client.lrange(key, -limit, -1)
            else:
                # 获取所有消息
                raw_messages = self.redis_client.lrange(key, 0, -1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg = json.loads(raw_msg)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
            
            return messages
        except Exception as e:
            print(f"Redis获取消息失败: {e}")
            return []
    
    def _get_messages_fallback(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """内存模式获取消息"""
        messages = self._fallback_memory.get(session_id, [])
        if limit:
            return messages[-limit:]
        return messages
    
    def clear_session(self, session_id: str) -> bool:
        """
        清除会话记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功清除
        """
        if self.use_redis:
            try:
                key = self._get_memory_key(session_id)
                self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"Redis清除会话失败: {e}")
                return False
        else:
            if session_id in self._fallback_memory:
                del self._fallback_memory[session_id]
            return True
    
    def get_session_count(self) -> int:
        """获取活跃会话数量"""
        if self.use_redis:
            try:
                pattern = f"{self.key_prefix}*"
                keys = self.redis_client.keys(pattern)
                return len(keys)
            except Exception as e:
                print(f"Redis获取会话数量失败: {e}")
                return 0
        else:
            return len(self._fallback_memory)
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话（主要用于内存模式）"""
        if not self.use_redis:  # Redis自动过期，不需要手动清理
            # 内存模式可以实现基于时间的清理逻辑
            # 这里简化处理，实际应用中可以加上时间检查
            pass
        return 0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "redis_available": REDIS_AVAILABLE,
            "using_redis": self.use_redis,
            "active_sessions": self.get_session_count(),
            "max_memory_length": self.max_memory_length,
            "memory_ttl_hours": self.memory_ttl / 3600,
            "key_prefix": self.key_prefix
        }


class SimpleMemory:
    """
    兼容性类：包装RedisMemory以保持与原有接口的兼容
    """
    
    def __init__(self, session_id: str, redis_memory: RedisMemory):
        self.session_id = session_id
        self.redis_memory = redis_memory
    
    @property
    def messages(self) -> List[Dict[str, Any]]:
        """获取消息列表（兼容原接口）"""
        return self.redis_memory.get_messages(self.session_id)
    
    def add_message(self, role: str, content: str):
        """添加消息（兼容原接口）"""
        return self.redis_memory.add_message(self.session_id, role, content)
    
    def clear(self):
        """清除记忆"""
        return self.redis_memory.clear_session(self.session_id)


# 全局Redis记忆管理器实例
_redis_memory_manager = None

def get_redis_memory_manager(**kwargs) -> RedisMemory:
    """获取全局Redis记忆管理器实例（懒加载）"""
    global _redis_memory_manager
    if _redis_memory_manager is None:
        _redis_memory_manager = RedisMemory(**kwargs)
    return _redis_memory_manager 