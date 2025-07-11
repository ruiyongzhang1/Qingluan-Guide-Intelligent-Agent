import warnings
import os
import asyncio
import time
import traceback

# 抑制LangChain弃用警告
import warnings
import os
import asyncio
import concurrent.futures
import traceback
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from dotenv import load_dotenv

# MCP 工具导入
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from langchain_mcp_adapters.tools import load_mcp_tools
    from langgraph.prebuilt import create_react_agent
    MCP_AVAILABLE = True
except ImportError:
    print("MCP工具不可用，将使用备用模式")
    MCP_AVAILABLE = False

# 导入提示词
try:
    from .prompts import (
        GENERAL_SYSTEM_PROMPT, 
        TRAVEL_SYSTEM_PROMPT, 
        PDF_PROMPT,
        INFORMATION_COLLECTOR_PROMPT,
        ITINERARY_PLANNER_PROMPT
    )
except ImportError:
    from prompts import (
        GENERAL_SYSTEM_PROMPT, 
        TRAVEL_SYSTEM_PROMPT, 
        PDF_PROMPT,
        INFORMATION_COLLECTOR_PROMPT,
        ITINERARY_PLANNER_PROMPT
    )

load_dotenv()

# 全局变量
user_agents = {}
mcp_tools = []

# =============================================================================
# MCP 工具加载
# =============================================================================
mcp_tools = []
user_agents = {}

async def load_mcp_tools_async():
    """异步加载MCP工具"""
    if not MCP_AVAILABLE:
        print("MCP工具不可用，返回空工具列表")
        return []
        
    try:
        # 直接使用绝对路径
        mcp_server_path = "mcp_server.py"
        
        if not os.path.exists(mcp_server_path):
            print(f"警告: MCP服务器文件不存在: {mcp_server_path}")
            return []
        
        # 创建服务器参数
        server_params = StdioServerParameters(
            command="python",
            args=[mcp_server_path],
            env={"SEARCHAPI_API_KEY": os.getenv("SEARCHAPI_API_KEY", "")}
        )
        
        # 使用标准MCP适配器加载工具
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化连接
                await session.initialize()
                
                # 获取工具
                tools = await load_mcp_tools(session)
                print(f"异步加载了 {len(tools)} 个MCP工具")
                return tools
                
    except Exception as e:
        print(f"异步加载MCP工具失败: {e}")
        return []

def load_mcp_tools_sync():
    """同步加载MCP工具的包装器"""
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tools = loop.run_until_complete(load_mcp_tools_async())
            return tools
        finally:
            loop.close()
    except Exception as e:
        print(f"同步加载MCP工具失败: {e}")
        return []

class MultiAgentTravelPlanner:
    """多智能体旅行规划系统（LangGraph版）"""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        load_dotenv()
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL")
        
        if not self.api_key:
            raise ValueError("未配置OpenAI API密钥")
        
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model="gpt-4.1",
            base_url=self.base_url,
            streaming=True
        )
        
        global mcp_tools
        if not mcp_tools:
            print("加载MCP工具...")
            mcp_tools = load_mcp_tools_sync()
        
        self.tools = mcp_tools
        print(f"可用工具数量: {len(self.tools)}")
        
        # 创建LangGraph智能体
        if self.tools:
            self.agent = create_react_agent(self.llm, self.tools)
            print("创建了LangGraph智能体")
        else:
            self.agent = None
            print("未创建智能体，工具加载失败")
    
    def get_response_stream(self, message: str, system_prompt: str = TRAVEL_SYSTEM_PROMPT):
        """获取流式响应（使用MCP工具的LangGraph智能体）"""
        try:
            # 如果有可用的MCP工具和LangGraph智能体，使用它们
            if self.agent and self.tools:
                print("MultiAgentTravelPlanner: 使用MCP智能体处理请求")
                
                def run_agent_sync():
                    """同步包装器来运行异步智能体"""
                    async def run_agent():
                        # 构建消息，包含系统提示和用户消息
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=message)
                        ]
                        
                        # 调用LangGraph智能体
                        response = await self.agent.ainvoke({"messages": messages})
                        
                        # 提取最后一条AI消息的内容
                        if response and "messages" in response:
                            last_message = response["messages"][-1]
                            if hasattr(last_message, 'content'):
                                return last_message.content
                            elif isinstance(last_message, dict) and 'content' in last_message:
                                return last_message['content']
                        
                        return "抱歉，未能获取到有效响应。"
                    
                    # 创建新的事件循环来运行异步代码
                    new_loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(new_loop)
                        return new_loop.run_until_complete(run_agent())
                    finally:
                        new_loop.close()
                
                # 在线程池中运行异步代码
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_agent_sync)
                    full_response = future.result(timeout=60)
            else:
                # 如果没有MCP工具，使用普通模型
                print("MultiAgentTravelPlanner: 未加载MCP工具，使用普通模型")
                non_streaming_llm = ChatOpenAI(
                    api_key=self.api_key,
                    model="gpt-4.1",
                    base_url=self.base_url,
                    streaming=True
                )
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ]
                
                # 获取完整响应
                response = non_streaming_llm.invoke(messages)
                full_response = response.content
            
            # 模拟流式输出
            chunk_size = 50  # 每次输出50个字符
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i+chunk_size]
                yield chunk
                        
        except Exception as e:
            yield f"处理请求时出现错误: {str(e)}"

class SimpleMemory:
    """简单的内存存储"""
    def __init__(self):
        self.messages = []
    
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        # 限制记忆长度
        if len(self.messages) > 60:  # 保留最近30轮对话
            self.messages = self.messages[-60:]

def get_agent_response_stream(user_message, user_email, agent_type="general", conv_id=None):
    """获取智能体响应流（使用配备MCP工具的LangGraph智能体）"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    
    if not api_key:
        raise ValueError("OPENAI API key not configured")
    
    # 选择系统提示
    if agent_type == "travel":
        system_prompt = TRAVEL_SYSTEM_PROMPT
    elif agent_type == "pdf_generator":
        system_prompt = PDF_PROMPT
    else:
        system_prompt = GENERAL_SYSTEM_PROMPT
    
    # 生成智能体标识
    agent_key = f"{user_email}_{agent_type}_{conv_id}" if conv_id else f"{user_email}_{agent_type}"
    
    try:
        # 检查是否已存在智能体实例
        if agent_key not in user_agents:
            # 创建新的智能体实例
            planner = MultiAgentTravelPlanner(user_email)
            memory = SimpleMemory()
            user_agents[agent_key] = {
                'planner': planner,
                'memory': memory,
                'agent_type': agent_type,
                'conv_id': conv_id
            }
        
        agent_instance = user_agents[agent_key]
        planner = agent_instance['planner']
        memory = agent_instance['memory']
        
        # 如果有可用的MCP工具和LangGraph智能体，使用它们
        if planner.agent and planner.tools:
            print("使用MCP智能体处理请求")
            # 异步运行LangGraph智能体
            try:
                def run_agent_sync():
                    """同步包装器来运行异步智能体"""
                    async def run_agent():
                        # 构建消息，包含系统提示和用户消息
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=user_message)
                        ]
                        
                        print(f"调用LangGraph智能体，消息数量: {len(messages)}")
                        # 调用LangGraph智能体
                        response = await planner.agent.ainvoke({"messages": messages})
                        print(f"收到智能体响应: {type(response)}")
                        
                        # 提取最后一条AI消息的内容
                        if response and "messages" in response:
                            last_message = response["messages"][-1]
                            if hasattr(last_message, 'content'):
                                return last_message.content
                            elif isinstance(last_message, dict) and 'content' in last_message:
                                return last_message['content']
                        
                        return "抱歉，未能获取到有效响应。"
                    
                    # 创建新的事件循环来运行异步代码
                    new_loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(new_loop)
                        return new_loop.run_until_complete(run_agent())
                    finally:
                        new_loop.close()
                        
                # 在线程池中运行异步代码
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_agent_sync)
                    full_response = future.result(timeout=60)
                        
            except Exception as agent_error:
                print(f"LangGraph智能体调用失败: {agent_error}")
                # 回退到普通模型
                model = ChatOpenAI(
                    api_key=api_key,
                    model="gpt-4.1",
                    base_url=base_url,
                    streaming=False
                )
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ]
                
                response = model.invoke(messages)
                full_response = response.content
        
        
        try:
            if hasattr(memory, 'add_message'):
                memory.add_message("user", user_message)
                memory.add_message("assistant", full_response)
            else:
                print("内存对象没有add_message方法")
        except Exception as e:
            print(f"保存记忆失败: {e}")
        
        # 将完整响应分成小块进行流式输出
        chunk_size = 50  # 每次输出50个字符
        for i in range(0, len(full_response), chunk_size):
            chunk = full_response[i:i+chunk_size]
            yield chunk
                    
    except Exception as e:
        # 清理无效的智能体实例
        if agent_key in user_agents:
            del user_agents[agent_key]
        print(f"智能体响应出错: {e}")
        # 提供备用响应
        yield f"抱歉，处理您的请求时出现了问题: {str(e)}"

def stream_model_response_sync(model, system_prompt, user_message):
    """同步流式调用模型响应"""
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        for chunk in model.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
                
    except Exception as e:
        yield f"模型调用失败: {str(e)}"

def is_travel_planning_request(message: str) -> bool:
    """判断是否为旅行规划请求"""
    travel_keywords = [
        '旅行', '旅游', '出行', '行程', '规划', '计划',
        '机票', '酒店', '住宿', '景点', '路线',
        'travel', 'trip', 'vacation', 'itinerary', 'plan',
        'flight', 'hotel', 'attraction', 'route'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in travel_keywords)

def handle_travel_planning_stream(travel_request: str, user_email: str, messages: list[BaseMessage], conv_id=None):
    """处理旅行相关请求的流式响应"""
    # 构建完整响应
    full_response = ""
    
    try:
        # 直接使用系统提示和消息构建完整响应
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_URL")
        
        model = ChatOpenAI(
            api_key=api_key,
            model="gpt-4.1",
            base_url=base_url,
            streaming=False  # 关闭流式处理，获取完整响应
        )
        
        # 判断是否为完整的旅行规划请求
        if is_travel_planning_request(travel_request):
            full_response = "\n\n## 🔍 正在制定旅行计划...\n\n"
            
            # 获取完整响应
            messages = [
                SystemMessage(content=TRAVEL_SYSTEM_PROMPT),
                HumanMessage(content=travel_request)
            ]
            response = model.invoke(messages)
            full_response += response.content
        else:
            # 一般的旅行问题
            messages = [
                SystemMessage(content=TRAVEL_SYSTEM_PROMPT),
                HumanMessage(content=travel_request)
            ]
            response = model.invoke(messages)
            full_response = response.content
        
        # 流式返回完整响应
        chunk_size = 50  # 每次输出50个字符
        for i in range(0, len(full_response), chunk_size):
            chunk = full_response[i:i+chunk_size]
            yield chunk
            
    except Exception as e:
        yield f"\n\n❌ 旅行规划过程中出现错误: {str(e)}\n\n"

def get_agent_response(user_message, user_email, agent_type="general", conv_id=None):
    """获取完整的AI响应（非流式）"""
    response_text = ""
    for chunk in get_agent_response_stream(user_message, user_email, agent_type, conv_id):
        response_text += chunk
    return response_text

async def get_mcp_response_async(user_message, user_email, agent_type="general"):
    """异步获取MCP响应（完全模仿test_mcp.py的成功模式）"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    
    if not api_key:
        raise ValueError("OPENAI API key not configured")
    
    try:
        print(f"[MCP] 开始MCP调用，用户: {user_email}, 类型: {agent_type}")
        
        # MCP服务器路径（与test_mcp.py完全相同）
        mcp_server_path = "mcp_server.py"
        
        if not os.path.exists(mcp_server_path):
            print(f"[MCP] 错误: MCP服务器文件不存在: {mcp_server_path}")
            return None
        
        print(f"[MCP] MCP服务器路径: {mcp_server_path}")
        
        # 创建服务器参数（与test_mcp.py完全相同）
        server_params = StdioServerParameters(
            command="python",
            args=[mcp_server_path],
            env={"SEARCHAPI_API_KEY": os.getenv("SEARCHAPI_API_KEY", "")}
        )
        
        print("[MCP] 正在连接MCP服务器...")
        
        # 使用标准MCP适配器加载工具（与test_mcp.py完全相同）
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("[MCP] MCP服务器连接成功，正在初始化...")
                
                # 初始化连接
                await session.initialize()
                print("[MCP] MCP会话初始化完成")
                
                # 获取工具
                tools = await load_mcp_tools(session)
                print(f"[MCP] 成功加载 {len(tools)} 个MCP工具:")
                
                for i, tool in enumerate(tools, 1):
                    print(f"[MCP]   {i}. {tool.name}: {tool.description}")
                
                if not tools:
                    print("[MCP] 警告: 没有加载到任何工具")
                    return None
                
                # 创建LLM（与test_mcp.py完全相同）
                llm = ChatOpenAI(
                    temperature=0.1,
                    api_key=api_key,
                    model="gpt-4.1",
                    base_url=base_url,
                    streaming=False
                )
                
                print("[MCP] 正在创建LangGraph智能体...")
                
                # 创建智能体（与test_mcp.py完全相同）
                agent = create_react_agent(llm, tools)
                print("[MCP] LangGraph智能体创建成功")
                
                # 测试查询（与test_mcp.py完全相同的消息格式）
                print(f"\n[MCP] 开始处理查询: {user_message[:100]}...")
                
                response = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})
                
                print("\n[MCP] 智能体响应:")
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    if hasattr(last_message, 'content'):
                        content = last_message.content
                        print(f"[MCP] 响应内容长度: {len(content)}")
                        print(f"[MCP] 响应内容前200字符: {content[:200]}...")
                        return content
                    else:
                        print(f"[MCP] 响应类型: {type(last_message)}")
                        print(f"[MCP] 响应内容: {last_message}")
                        return str(last_message)
                else:
                    print(f"[MCP] 意外的响应格式: {response}")
                    return None
                
                print("\n[MCP] MCP工具调用完成！")
                
    except Exception as e:
        print(f"[MCP] 调用过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_mcp_response_sync(user_message, user_email, agent_type="general"):
    """同步调用MCP响应"""
    try:
        return asyncio.run(get_mcp_response_async(user_message, user_email, agent_type))
    except Exception as e:
        print(f"[MCP] 同步调用失败: {e}")
        return None

async def multi_agent_travel_planning_async(user_request, user_email):
    """多智能体旅行规划流水线（异步版本）"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    
    if not api_key:
        raise ValueError("OPENAI API key not configured")
    
    try:
        print(f"[多智能体] 开始多智能体旅行规划，用户: {user_email}")
        
        # MCP服务器路径
        mcp_server_path = "mcp_server.py"
        
        if not os.path.exists(mcp_server_path):
            print(f"[多智能体] 错误: MCP服务器文件不存在: {mcp_server_path}")
            return None
        
        # 创建服务器参数
        server_params = StdioServerParameters(
            command="python",
            args=[mcp_server_path],
            env={"SEARCHAPI_API_KEY": os.getenv("SEARCHAPI_API_KEY", "")}
        )
        
        print("[多智能体] 正在连接MCP服务器...")
        
        # 使用MCP工具
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("[多智能体] MCP服务器连接成功，正在初始化...")
                
                # 初始化连接
                await session.initialize()
                print("[多智能体] MCP会话初始化完成")
                
                # 获取工具
                tools = await load_mcp_tools(session)
                print(f"[多智能体] 成功加载 {len(tools)} 个MCP工具")
                
                if not tools:
                    print("[多智能体] 警告: 没有加载到任何工具")
                    return None
                
                # 创建LLM
                llm = ChatOpenAI(
                    api_key=api_key,
                    model="gpt-4.1",
                    base_url=base_url,
                    streaming=False
                )
                
                # 阶段1: 信息收集智能体
                print("\n[多智能体] === 阶段1: 信息收集智能体 ===")
                print("[多智能体] 正在创建信息收集智能体...")
                
                collector_agent = create_react_agent(llm, tools)
                print("[多智能体] 信息收集智能体创建成功")
                
                # 构建信息收集请求
                collector_request = f"""
{INFORMATION_COLLECTOR_PROMPT}

用户旅行需求：
{user_request}

请使用所有可用的搜索工具收集相关的旅行信息。
"""
                
                print(f"[多智能体] 开始信息收集，请求长度: {len(collector_request)}")
                
                # 执行信息收集
                collector_response = await collector_agent.ainvoke({
                    "messages": [{"role": "user", "content": collector_request}]
                })
                
                # 提取信息收集结果
                collected_info = ""
                if collector_response and "messages" in collector_response:
                    last_message = collector_response["messages"][-1]
                    if hasattr(last_message, 'content'):
                        collected_info = last_message.content
                    else:
                        collected_info = str(last_message)
                
                print(f"[多智能体] 信息收集完成，收集到的信息长度: {len(collected_info)}")
                print(f"[多智能体] 信息收集前300字符: {collected_info[:300]}...")
                
                # 阶段2: 行程规划智能体
                print("\n[多智能体] === 阶段2: 行程规划智能体 ===")
                print("[多智能体] 正在创建行程规划智能体...")
                
                planner_agent = create_react_agent(llm, tools)
                print("[多智能体] 行程规划智能体创建成功")
                
                # 构建行程规划请求
                planner_request = f"""
{ITINERARY_PLANNER_PROMPT}

## 用户原始需求：
{user_request}

## 信息收集智能体提供的详细信息：
{collected_info}

请基于以上收集到的详细信息，为用户制定完整的个性化旅行方案。
请确保充分利用收集到的具体信息（价格、地址、时间等），制定可执行的旅行计划。
"""
                
                print(f"[多智能体] 开始行程规划，请求长度: {len(planner_request)}")
                
                # 执行行程规划
                planner_response = await planner_agent.ainvoke({
                    "messages": [{"role": "user", "content": planner_request}]
                })
                
                # 提取行程规划结果
                travel_plan = ""
                if planner_response and "messages" in planner_response:
                    last_message = planner_response["messages"][-1]
                    if hasattr(last_message, 'content'):
                        travel_plan = last_message.content
                    else:
                        travel_plan = str(last_message)
                
                print(f"[多智能体] 行程规划完成，规划方案长度: {len(travel_plan)}")
                print(f"[多智能体] 规划方案前300字符: {travel_plan[:300]}...")
                
                # 合并最终结果
                final_result = f"""# 🎯 专业旅行规划方案

## 📋 规划流程说明
本方案通过两个专业智能体协作完成：
1. **信息收集智能体**：使用实时搜索工具收集最新的旅行信息
2. **行程规划智能体**：基于收集的信息制定个性化旅行方案

---

{travel_plan}

---

## 📊 信息收集详情
<details>
<summary>点击查看详细的信息收集过程</summary>

{collected_info}

</details>

---

*本规划方案由AI多智能体系统生成，基于实时搜索的最新信息制定。*
"""
                
                print(f"[多智能体] 多智能体规划完成，最终结果长度: {len(final_result)}")
                return final_result
                
    except Exception as e:
        print(f"[多智能体] 多智能体规划过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def multi_agent_travel_planning_sync(user_request, user_email):
    """多智能体旅行规划流水线（同步版本）"""
    try:
        return asyncio.run(multi_agent_travel_planning_async(user_request, user_email))
    except Exception as e:
        print(f"[多智能体] 同步调用失败: {e}")
        return None
