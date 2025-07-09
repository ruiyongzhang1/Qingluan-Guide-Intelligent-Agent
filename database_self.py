import sqlite3
import json
from datetime import datetime
import os
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: str = 'app.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建对话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
            )
        ''')
        
        # 创建消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                text TEXT NOT NULL,
                is_user BOOLEAN NOT NULL,
                agent_type TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        ''')
        
        # # 创建索引以提高查询性能
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_email ON conversations (user_email)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at)')
        
        conn.commit()
        conn.close()
    
    def add_user(self, email: str, password: str) -> bool:
        """添加新用户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT INTO users (email, password) VALUES (?, ?)',
                (email, password)
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # 用户已存在
            conn.close()
            return False
        except Exception as e:
            print(f"Error adding user: {e}")
            conn.close()
            return False
    
    def verify_user(self, email: str, password: str) -> bool:
        """验证用户登录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT password FROM users WHERE email = ?',
                (email,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result['password'] == password:
                return True
            return False
        except Exception as e:
            print(f"Error verifying user: {e}")
            conn.close()
            return False
    
    def save_conversation(self, email: str, messages: List[Dict[str, Any]], conv_id: str):
        """保存对话和消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 检查对话是否已存在
            cursor.execute(
                'SELECT id FROM conversations WHERE id = ?',
                (conv_id,)
            )
            
            if not cursor.fetchone():
                # 创建新对话
                cursor.execute(
                    'INSERT INTO conversations (id, user_email, date) VALUES (?, ?, ?)',
                    (conv_id, email, today)
                )
            
            # 保存消息
            for message in messages:
                cursor.execute(
                    'INSERT INTO messages (conversation_id, text, is_user, agent_type) VALUES (?, ?, ?, ?)',
                    (
                        conv_id,
                        message.get('text', ''),
                        message.get('is_user', False),
                        message.get('agent_type', 'general')
                    )
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving conversation: {e}")
            conn.close()
            raise
    
    def get_history(self, email: str) -> List[Dict[str, Any]]:
        """获取用户的历史对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取所有对话及其消息
            cursor.execute('''
                SELECT 
                    c.id,
                    c.date,
                    c.created_at,
                    COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_email = ?
                GROUP BY c.id
                ORDER BY c.created_at DESC
            ''', (email,))
            
            conversations = []
            for row in cursor.fetchall():
                # 获取对话的消息
                cursor.execute('''
                    SELECT text, is_user, agent_type, created_at
                    FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                ''', (row['id'],))
                
                messages = []
                for msg_row in cursor.fetchall():
                    messages.append({
                        'text': msg_row['text'],
                        'is_user': bool(msg_row['is_user']),
                        'agent_type': msg_row['agent_type'],
                        'created_at': msg_row['created_at']
                    })
                
                conversations.append({
                    'id': row['id'],
                    'date': row['date'],
                    'created_at': row['created_at'],
                    'message_count': row['message_count'],
                    'messages': messages
                })
            
            conn.close()
            return conversations
        except Exception as e:
            print(f"Error getting history: {e}")
            conn.close()
            return []
    
    def clear_user_history(self, email: str) -> bool:
        """清除用户的所有历史记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            #首先删除所有与会话相关的消息
            cursor.execute(
                'DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_email = ?)',
                (email,)
            )
            
            # 删除用户的所有对话（消息会通过外键约束自动删除）
            cursor.execute(
                'DELETE FROM conversations WHERE user_email = ?',
                (email,)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing user history: {e}")
            conn.close()
            return False
    
    def get_conversation_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        """获取特定对话的所有消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT text, is_user, agent_type, created_at
                FROM messages 
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            ''', (conv_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'text': row['text'],
                    'is_user': bool(row['is_user']),
                    'agent_type': row['agent_type'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return messages
        except Exception as e:
            print(f"Error getting conversation messages: {e}")
            conn.close()
            return []
    
    def delete_conversation(self, conv_id: str) -> bool:
        """删除特定对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 首先删除该对话的所有消息
            cursor.execute(
                'DELETE FROM messages WHERE conversation_id = ?',
                (conv_id,)
            )
            
            # 然后删除对话本身
            cursor.execute(
                'DELETE FROM conversations WHERE id = ?',
                (conv_id,)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            conn.close()
            return False
    
    def delete_conversation_for_user(self, email: str, conv_id: str) -> bool:
        """删除特定用户的特定对话（验证权限）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 首先验证对话是否属于该用户
            cursor.execute(
                'SELECT id FROM conversations WHERE id = ? AND user_email = ?',
                (conv_id, email)
            )
            
            if not cursor.fetchone():
                conn.close()
                return False  # 对话不存在或不属于该用户
            
            # 删除该对话的所有消息
            cursor.execute(
                'DELETE FROM messages WHERE conversation_id = ?',
                (conv_id,)
            )
            
            # 删除对话本身
            cursor.execute(
                'DELETE FROM conversations WHERE id = ? AND user_email = ?',
                (conv_id, email)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting conversation for user: {e}")
            conn.close()
            return False
    
    def get_user_stats(self, email: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 总对话数
            cursor.execute(
                'SELECT COUNT(*) as conv_count FROM conversations WHERE user_email = ?',
                (email,)
            )
            conv_count = cursor.fetchone()['conv_count']
            
            # 总消息数
            cursor.execute('''
                SELECT COUNT(*) as msg_count 
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_email = ?
            ''', (email,))
            msg_count = cursor.fetchone()['msg_count']
            
            # 最近活跃时间
            cursor.execute('''
                SELECT MAX(created_at) as last_active
                FROM conversations 
                WHERE user_email = ?
            ''', (email,))
            last_active = cursor.fetchone()['last_active']
            
            conn.close()
            
            return {
                'conversation_count': conv_count,
                'message_count': msg_count,
                'last_active': last_active
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            conn.close()
            return {
                'conversation_count': 0,
                'message_count': 0,
                'last_active': None
            }

# 创建全局数据库实例
db = Database() 