#!/usr/bin/env python3
"""
Redis智能体记忆查看器
提供友好的界面来查看和管理Redis中存储的智能体记忆数据
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any
from agent.redis_memory import get_redis_memory_manager

def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title: str):
    """打印小节标题"""
    print(f"\n📋 {title}")
    print("-" * 40)

def format_timestamp(timestamp_str: str) -> str:
    """格式化时间戳"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str

def format_content(content: str, max_length: int = 50) -> str:
    """格式化内容，限制长度"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."

def view_all_sessions(redis_manager):
    """查看所有会话"""
    print_section("所有智能体记忆会话")
    
    try:
        if redis_manager.use_redis:
            pattern = f"{redis_manager.key_prefix}*"
            keys = redis_manager.redis_client.keys(pattern)
            
            if not keys:
                print("❌ 没有找到任何记忆会话")
                return []
            
            print(f"📊 共找到 {len(keys)} 个记忆会话:")
            
            sessions = []
            for i, key in enumerate(keys, 1):
                # 解析会话信息
                session_id = key.replace(redis_manager.key_prefix, "")
                if "_" in session_id:
                    email, conv_id = session_id.split("_", 1)
                else:
                    email, conv_id = session_id, "unknown"
                
                # 获取消息数量
                try:
                    msg_count = redis_manager.redis_client.llen(key)
                    ttl = redis_manager.redis_client.ttl(key)
                    ttl_str = f"{ttl//3600}h{(ttl%3600)//60}m" if ttl > 0 else "永久" if ttl == -1 else "已过期"
                except:
                    msg_count = "?"
                    ttl_str = "?"
                
                sessions.append({
                    'index': i,
                    'session_id': session_id,
                    'email': email,
                    'conv_id': conv_id,
                    'msg_count': msg_count,
                    'ttl': ttl_str,
                    'key': key
                })
                
                print(f"  {i:2d}. {email} | 消息:{msg_count} | 过期:{ttl_str}")
            
            return sessions
        else:
            print("❌ Redis不可用，显示内存模式会话:")
            sessions = []
            for i, (session_id, messages) in enumerate(redis_manager._fallback_memory.items(), 1):
                if "_" in session_id:
                    email, conv_id = session_id.split("_", 1)
                else:
                    email, conv_id = session_id, "unknown"
                
                sessions.append({
                    'index': i,
                    'session_id': session_id,
                    'email': email,
                    'conv_id': conv_id,
                    'msg_count': len(messages),
                    'ttl': "内存模式",
                    'key': session_id
                })
                
                print(f"  {i:2d}. {email} | 消息:{len(messages)} | 模式:内存")
            
            return sessions
            
    except Exception as e:
        print(f"❌ 查看会话失败: {e}")
        return []

def view_session_details(redis_manager, session_id: str):
    """查看特定会话的详细信息"""
    print_section(f"会话详情: {session_id}")
    
    try:
        messages = redis_manager.get_messages(session_id)
        
        if not messages:
            print("❌ 该会话没有记忆消息")
            return
        
        print(f"📝 共有 {len(messages)} 条记忆消息:\n")
        
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            role_icon = "👤" if role == "user" else "🤖" if role == "assistant" else "❓"
            time_str = format_timestamp(timestamp)
            
            print(f"  {i:2d}. {role_icon} [{role}] {time_str}")
            print(f"      {content}")
            print()
            
    except Exception as e:
        print(f"❌ 查看会话详情失败: {e}")

def view_user_sessions(redis_manager, email: str):
    """查看特定用户的所有会话"""
    print_section(f"用户 {email} 的所有会话")
    
    try:
        if redis_manager.use_redis:
            pattern = f"{redis_manager.key_prefix}{email}_*"
            keys = redis_manager.redis_client.keys(pattern)
        else:
            keys = [k for k in redis_manager._fallback_memory.keys() if k.startswith(f"{email}_")]
        
        if not keys:
            print(f"❌ 用户 {email} 没有任何记忆会话")
            return
        
        print(f"📊 用户 {email} 共有 {len(keys)} 个会话:")
        
        for i, key in enumerate(keys, 1):
            if redis_manager.use_redis:
                session_id = key.replace(redis_manager.key_prefix, "")
                msg_count = redis_manager.redis_client.llen(key)
            else:
                session_id = key
                msg_count = len(redis_manager._fallback_memory[key])
            
            conv_id = session_id.split("_", 1)[1] if "_" in session_id else "unknown"
            print(f"  {i:2d}. 会话ID: {conv_id[:8]}... | 消息数: {msg_count}")
            
    except Exception as e:
        print(f"❌ 查看用户会话失败: {e}")

def redis_stats(redis_manager):
    """显示Redis统计信息"""
    print_section("Redis统计信息")
    
    try:
        stats = redis_manager.get_memory_stats()
        
        print(f"🔌 Redis可用: {'✅' if stats['redis_available'] else '❌'}")
        print(f"💾 使用Redis: {'✅' if stats['using_redis'] else '❌ (内存模式)'}")
        print(f"📊 活跃会话: {stats['active_sessions']}")
        print(f"📏 最大记忆长度: {stats['max_memory_length']} 条")
        print(f"⏰ 记忆过期时间: {stats['memory_ttl_hours']} 小时")
        print(f"🔑 键前缀: {stats['key_prefix']}")
        
        if redis_manager.use_redis:
            # 获取Redis服务器信息
            info = redis_manager.redis_client.info()
            print(f"🖥️  Redis版本: {info.get('redis_version', 'Unknown')}")
            print(f"💡 已使用内存: {info.get('used_memory_human', 'Unknown')}")
            print(f"👥 连接的客户端: {info.get('connected_clients', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")

def search_memories(redis_manager, keyword: str):
    """搜索包含关键词的记忆"""
    print_section(f"搜索关键词: '{keyword}'")
    
    found_count = 0
    
    try:
        if redis_manager.use_redis:
            pattern = f"{redis_manager.key_prefix}*"
            keys = redis_manager.redis_client.keys(pattern)
            
            for key in keys:
                session_id = key.replace(redis_manager.key_prefix, "")
                messages = redis_manager.get_messages(session_id)
                
                for i, msg in enumerate(messages):
                    if keyword.lower() in msg.get('content', '').lower():
                        if found_count == 0:
                            print("🔍 找到以下匹配的记忆:")
                        
                        found_count += 1
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        timestamp = format_timestamp(msg.get('timestamp', ''))
                        
                        print(f"\n  {found_count}. 【{session_id.split('_')[0]}】{timestamp}")
                        print(f"     [{role}] {content}")
        
        else:
            for session_id, messages in redis_manager._fallback_memory.items():
                for msg in messages:
                    if keyword.lower() in msg.get('content', '').lower():
                        if found_count == 0:
                            print("🔍 找到以下匹配的记忆:")
                        
                        found_count += 1
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        timestamp = format_timestamp(msg.get('timestamp', ''))
                        
                        print(f"\n  {found_count}. 【{session_id.split('_')[0]}】{timestamp}")
                        print(f"     [{role}] {content}")
        
        if found_count == 0:
            print(f"❌ 没有找到包含 '{keyword}' 的记忆")
        else:
            print(f"\n📊 共找到 {found_count} 条匹配的记忆")
            
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

def interactive_menu():
    """交互式菜单"""
    print_header("🧠 Redis智能体记忆查看器")
    
    try:
        redis_manager = get_redis_memory_manager()
        print(f"✅ 连接成功 ({'Redis模式' if redis_manager.use_redis else '内存模式'})")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
    
    while True:
        print("\n" + "─" * 40)
        print("🔧 请选择操作:")
        print("  1. 查看所有会话")
        print("  2. 查看特定会话详情")
        print("  3. 查看特定用户的会话")
        print("  4. 搜索记忆内容")
        print("  5. 查看Redis统计信息")
        print("  6. 退出")
        print("─" * 40)
        
        try:
            choice = input("请输入选项 (1-6): ").strip()
            
            if choice == "1":
                sessions = view_all_sessions(redis_manager)
                
            elif choice == "2":
                sessions = view_all_sessions(redis_manager)
                if sessions:
                    try:
                        index = int(input(f"请输入会话编号 (1-{len(sessions)}): ")) - 1
                        if 0 <= index < len(sessions):
                            view_session_details(redis_manager, sessions[index]['session_id'])
                        else:
                            print("❌ 无效的会话编号")
                    except ValueError:
                        print("❌ 请输入有效的数字")
                        
            elif choice == "3":
                email = input("请输入用户邮箱: ").strip()
                if email:
                    view_user_sessions(redis_manager, email)
                else:
                    print("❌ 邮箱不能为空")
                    
            elif choice == "4":
                keyword = input("请输入搜索关键词: ").strip()
                if keyword:
                    search_memories(redis_manager, keyword)
                else:
                    print("❌ 关键词不能为空")
                    
            elif choice == "5":
                redis_stats(redis_manager)
                
            elif choice == "6":
                print("👋 再见!")
                break
                
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n\n👋 退出程序")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        command = sys.argv[1].lower()
        redis_manager = get_redis_memory_manager()
        
        if command == "stats":
            redis_stats(redis_manager)
        elif command == "list":
            view_all_sessions(redis_manager)
        elif command == "search" and len(sys.argv) > 2:
            search_memories(redis_manager, sys.argv[2])
        else:
            print("用法:")
            print("  python redis_viewer.py              # 交互式模式")
            print("  python redis_viewer.py stats        # 查看统计信息")
            print("  python redis_viewer.py list         # 列出所有会话")
            print("  python redis_viewer.py search 关键词 # 搜索记忆")
    else:
        # 交互式模式
        interactive_menu()

if __name__ == "__main__":
    main() 