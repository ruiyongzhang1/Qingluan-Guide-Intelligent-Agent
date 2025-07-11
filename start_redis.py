#!/usr/bin/env python3
"""
Redis服务器启动脚本
用于快速启动Redis服务器以支持AI智能体的记忆功能
"""

import os
import sys
import subprocess
import platform
import time

def start_redis_windows():
    """在Windows上启动Redis服务器"""
    redis_path = os.path.join("redis", "redis-server.exe")
    config_path = os.path.join("redis", "redis.windows.conf")
    
    if not os.path.exists(redis_path):
        print("❌ Redis服务器可执行文件未找到")
        print(f"   预期路径: {redis_path}")
        return False
    
    if not os.path.exists(config_path):
        print("⚠️  Redis配置文件未找到，使用默认配置")
        config_path = None
    
    try:
        print("🚀 正在启动Redis服务器...")
        if config_path:
            cmd = [redis_path, config_path]
        else:
            cmd = [redis_path]
        
        # 在新窗口中启动Redis
        if platform.system() == "Windows":
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(cmd)
        
        print("✅ Redis服务器启动成功!")
        print("   默认地址: localhost:6379")
        print("   要停止Redis，请关闭Redis窗口或按Ctrl+C")
        return True
        
    except Exception as e:
        print(f"❌ 启动Redis失败: {e}")
        return False

def start_redis_linux():
    """在Linux/Mac上启动Redis服务器"""
    try:
        # 检查Redis是否已安装
        result = subprocess.run(["which", "redis-server"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Redis未安装，请先安装Redis:")
            print("   Ubuntu/Debian: sudo apt-get install redis-server")
            print("   CentOS/RHEL: sudo yum install redis")
            print("   macOS: brew install redis")
            return False
        
        print("🚀 正在启动Redis服务器...")
        subprocess.Popen(["redis-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待一下让Redis启动
        time.sleep(2)
        
        # 检查Redis是否成功启动
        try:
            result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == "PONG":
                print("✅ Redis服务器启动成功!")
                print("   默认地址: localhost:6379")
                return True
            else:
                print("❌ Redis启动失败")
                return False
        except subprocess.TimeoutExpired:
            print("⚠️  Redis可能正在启动中...")
            return True
            
    except Exception as e:
        print(f"❌ 启动Redis失败: {e}")
        return False

def check_redis_status():
    """检查Redis服务器状态"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        print("✅ Redis服务器运行正常")
        
        # 获取一些基本信息
        info = client.info()
        print(f"   Redis版本: {info.get('redis_version', 'Unknown')}")
        print(f"   已使用内存: {info.get('used_memory_human', 'Unknown')}")
        print(f"   连接的客户端: {info.get('connected_clients', 'Unknown')}")
        return True
        
    except ImportError:
        print("⚠️  redis包未安装，请运行: pip install redis==5.0.1")
        return False
    except Exception as e:
        print(f"❌ Redis服务器不可用: {e}")
        print("   请确保Redis服务器正在运行")
        return False

def main():
    print("🧠 AI智能体Redis记忆系统启动工具")
    print("=" * 50)
    
    # 首先检查当前状态
    if check_redis_status():
        print("\n✨ Redis已经在运行，无需重复启动")
        return
    
    print("\n📋 检测到Redis未运行，正在启动...")
    
    system = platform.system()
    if system == "Windows":
        success = start_redis_windows()
    else:
        success = start_redis_linux()
    
    if success:
        print("\n🎉 Redis启动完成！")
        print("\n📝 使用说明:")
        print("   1. 现在可以启动app.py来使用AI智能体")
        print("   2. 智能体的对话记忆将持久化存储在Redis中")
        print("   3. 即使重启应用，对话历史也不会丢失")
        print("   4. 访问 /memory_stats 查看记忆系统统计")
        
        # 等待一下再次检查状态
        print("\n🔍 验证Redis状态...")
        time.sleep(3)
        check_redis_status()
    else:
        print("\n💡 替代方案:")
        print("   如果Redis启动失败，系统会自动回退到内存模式")
        print("   内存模式下对话记忆不会持久化，但功能正常")

if __name__ == "__main__":
    main() 