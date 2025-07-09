from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import Tool
import requests
import json
import time
from typing import List, Dict, Optional
import asyncio
import aiohttp
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

# ===== 数据模型 =====
@dataclass
class Attraction:
    name: str
    address: str
    latitude: float
    longitude: float
    category: str
    rating: float
    distance: float
    description: str = ""
    phone: str = ""
    opening_hours: str = ""
    ticket_price: str = ""

# ===== API服务层 =====
class MapAPIService:
    """地图API服务类"""
    
    def __init__(self, gaode_key: str = None):
        self.gaode_key = gaode_key or "d24e7f7d507304fda88b6bc4b1968c65"
        self.cache = {}
        self.cache_expiry = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]
    
    def _set_cache(self, key: str, data: any, expiry_hours: int = 24):
        """设置缓存"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(hours=expiry_hours)
    
    def get_nearby_attractions_gaode(self, location: str, radius: int = 5000) -> List[Attraction]:
        """使用高德地图API获取附近景点"""
        cache_key = f"gaode_{location}_{radius}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # 1. 先获取地点坐标
            geocode_url = "https://restapi.amap.com/v3/geocode/geo"
            geocode_params = {
                "key": self.gaode_key,
                "address": location,
                "output": "json"
            }
            
            geo_response = requests.get(geocode_url, params=geocode_params, timeout=10)
            geo_data = geo_response.json()
            
            if geo_data["status"] != "1" or not geo_data["geocodes"]:
                return self._get_mock_attractions(location)
            
            coordinate = geo_data["geocodes"][0]["location"]
            
            # 2. 搜索附近景点
            search_url = "https://restapi.amap.com/v3/place/around"
            search_params = {
                "key": self.gaode_key,
                "location": coordinate,
                "keywords": "风景名胜|旅游景点|博物馆|公园|寺庙|古迹",
                "radius": radius,
                "output": "json",
                "extensions": "all"
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_data = search_response.json()
            
            attractions = []
            if search_data["status"] == "1" and search_data["pois"]:
                for poi in search_data["pois"][:15]:
                    location_parts = poi.get("location", "0,0").split(",")
                    attraction = Attraction(
                        name=poi.get("name", ""),
                        address=poi.get("address", ""),
                        latitude=float(location_parts[1]) if len(location_parts) > 1 else 0,
                        longitude=float(location_parts[0]) if len(location_parts) > 0 else 0,
                        category=poi.get("type", "景点"),
                        rating=float(poi.get("biz_ext", {}).get("rating", "0") or "0"),
                        distance=float(poi.get("distance", "0")),
                        phone=poi.get("tel", ""),
                        description=poi.get("business_area", "")
                    )
                    attractions.append(attraction)
            
            self._set_cache(cache_key, attractions)
            return attractions
            
        except Exception as e:
            print(f"高德API调用失败: {e}")
            return self._get_mock_attractions(location)
    
    def _get_mock_attractions(self, location: str) -> List[Attraction]:
        """模拟景点数据（当API失败时使用）"""
        mock_data = {
            "北京": [
                Attraction("故宫博物院", "北京市东城区景山前街4号", 39.9163, 116.3903, "历史文化", 4.7, 1000),
                Attraction("天安门广场", "北京市东城区天安门广场", 39.9059, 116.3974, "历史文化", 4.6, 800),
                Attraction("颐和园", "北京市海淀区新建宫门路19号", 39.9999, 116.2755, "园林景观", 4.5, 2000),
                Attraction("八达岭长城", "北京市延庆区军都山关沟古道北口", 40.3577, 116.0154, "历史文化", 4.8, 60000),
                Attraction("天坛公园", "北京市东城区天坛内东里7号", 39.8732, 116.4119, "历史文化", 4.4, 1500)
            ],
            "杭州": [
                Attraction("西湖", "浙江省杭州市西湖区", 30.2477, 120.1503, "自然风光", 4.6, 500),
                Attraction("雷峰塔", "浙江省杭州市西湖区南山路15号", 30.2311, 120.1492, "历史文化", 4.3, 800),
                Attraction("灵隐寺", "浙江省杭州市西湖区法云弄1号", 30.2415, 120.1009, "宗教场所", 4.5, 1200),
                Attraction("千岛湖", "浙江省杭州市淳安县", 29.6054, 119.0423, "自然风光", 4.4, 80000),
                Attraction("宋城", "浙江省杭州市之江路148号", 30.1982, 120.1267, "主题公园", 4.2, 2000)
            ]
        }
        
        for city, attractions in mock_data.items():
            if city in location:
                return attractions
        
        # 默认返回一些通用景点
        return [
            Attraction("当地博物馆", f"{location}市中心", 0, 0, "历史文化", 4.0, 1000),
            Attraction("城市公园", f"{location}公园路", 0, 0, "自然风光", 4.2, 800),
            Attraction("古城墙", f"{location}老城区", 0, 0, "历史文化", 4.1, 1200)
        ]

class SearchAPIService:
    """搜索API服务类"""
    
    def __init__(self):
        # 简化版本，不使用外部搜索API，而是使用内置知识
        self.cache = {}
        self.cache_expiry = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]
    
    def _set_cache(self, key: str, data: str, expiry_hours: int = 6):
        """设置缓存"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(hours=expiry_hours)
    
    def search_attraction_info(self, attraction_name: str, city: str = "") -> str:
        """获取景点详细信息（使用内置知识库）"""
        cache_key = f"search_{attraction_name}_{city}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        # 简化版：返回基本提示，让AI使用其内置知识
        info = f"请基于您的知识库为{attraction_name}提供详细介绍，包括历史背景、文化价值、建筑特色、参观建议等信息。"
        
        self._set_cache(cache_key, info)
        return info

# ===== 增强版导游智能体 =====
class EnhancedTourGuideAgent:
    def __init__(self, gaode_key: str = None):
        load_dotenv()
        
        # 获取API配置 - 使用OpenAI API
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL")
        
        if not self.api_key:
            raise ValueError("未配置OpenAI API密钥")
        
        # 初始化大模型 - 使用OpenAI的gpt-4.1-nano模型
        self.llm = ChatOpenAI(
            temperature=0.7,
            api_key=SecretStr(self.api_key),
            model="gpt-4.1-nano",  # 使用gpt-4.1-nano模型
            base_url=self.base_url,
            streaming=True
        )
        
        # 初始化服务
        self.map_service = MapAPIService(gaode_key)
        self.search_service = SearchAPIService()
        
        # 初始化记忆
        self.memory = ConversationBufferMemory(
            memory_key="history",
            return_messages=True
        )
        
        self.current_style = "学术型"
        self.current_attractions = []
        self.chain = self._create_chain()
    
    def _create_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self._get_enhanced_system_prompt()),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        return prompt | self.llm | StrOutputParser()
    
    def _get_enhanced_system_prompt(self) -> str:
        """增强版系统提示词"""
        style_prompts = {
            "学术型": "作为考古学专家，用严谨数据讲解，所有结论需标注来源",
            "故事型": "作为说书人，用生动叙事和感官描述（至少3个形容词）",
            "亲子型": "使用简单词汇和互动问题（语句<20字，带拟声词）",
            "网红风格": "加入emoji和拍照建议（推荐3个机位参数）",
            "幽默诙谐": "用轻松搞笑的方式讲解，穿插网络流行语和段子"
        }
        
        return f"""
        你是一名专业AI导游，当前使用【{self.current_style}】风格讲解。
        {style_prompts.get(self.current_style, "")}
        
        特别说明：
        1. 用户提供的景点信息来自真实的地图API数据
        2. 搜索信息来自最新的网络资源，请整合这些信息
        3. 如果搜索信息与你的知识有冲突，优先使用搜索到的最新信息
        4. 必须在回答中体现搜索到的实时信息（如门票价格、开放时间等）
        5. 始终使用Markdown格式回复
        
        必须遵守：
        1. 历史日期同时显示农历/公历
        2. 距离数据用公制/英制单位
        3. 宗教场所自动追加注意事项
        4. 餐饮信息标注人均消费区间
        5. 引用搜索信息时要自然融入，不要生硬标注"根据搜索"
        6. 每个小点单独成行，确保良好的可读性
        
        输出格式要求：
        
        # 🏛️ **景点名称**
        
        ## 📖 总体概况
        （1-2句话简要介绍）
        
        ## 📍 地理位置
        详细地址和位置信息
        
        ## ⏳ 历史时期
        建造时间和历史背景
        
        ## 🌟 核心亮点
        - 亮点1
        - 亮点2  
        - 亮点3
        - 亮点4
        - 亮点5
        
        ## 📜 深度讲解
        400-500字的详细历史背景、建筑特色和文化意义介绍
        
        ## 🎫 实用信息
        - **开放时间**：具体时间
        - **门票价格**：具体价格
        - **交通方式**：详细交通指南
        - **联系电话**：电话号码（如有）
        
        ## 💡 参观建议
        - 建议1
        - 建议2
        - 建议3
        
        ## ⚠️ 注意事项
        - 注意事项1
        - 注意事项2
        - 注意事项3
        """
    
    def set_style(self, style: str):
        """设置讲解风格"""
        valid_styles = ["学术型", "故事型", "亲子型", "网红风格", "幽默诙谐"]
        if style in valid_styles:
            self.current_style = style
            self.chain = self._create_chain()
            return f"已切换为【{style}】讲解风格"
        return "无效的风格选择"
    
    def get_nearby_attractions(self, location: str, radius: int = 5000) -> List[Attraction]:
        """获取附近景点"""
        print(f"🔍 正在搜索 {location} 附近 {radius/1000}km 范围内的景点...")
        attractions = self.map_service.get_nearby_attractions_gaode(location, radius)
        self.current_attractions = attractions
        return attractions
    
    def introduce_attraction_with_search(self, attraction: Attraction, city: str = "") -> str:
        """使用搜索增强的景点介绍"""
        print(f"🔍 正在搜索 {attraction.name} 的最新信息...")
        
        # 搜索景点最新信息
        search_info = self.search_service.search_attraction_info(attraction.name, city)
        
        # 构建增强的查询
        query = f"""
        请用{self.current_style}风格详细介绍以下景点：
        
        【景点基本信息】（来自地图API）：
        - 名称：{attraction.name}
        - 地址：{attraction.address}
        - 坐标：{attraction.latitude}, {attraction.longitude}
        - 类型：{attraction.category}
        - 评分：{attraction.rating}/5.0
        - 距离：{attraction.distance}米
        - 电话：{attraction.phone or "暂无"}
        - 简介：{attraction.description or "暂无"}
        
        【最新搜索信息】：
        {search_info}
        
        请整合以上信息，生成专业的景点介绍。特别注意要自然融入搜索到的最新信息。
        """
        
        # 调用模型
        response = self.chain.invoke({
            "input": query,
            "history": self.memory.load_memory_variables({})["history"]
        })
        
        # 保存到记忆
        self.memory.save_context(
            {"input": f"介绍{attraction.name}"},
            {"output": response}
        )
        
        return response
    
    def filter_attractions(self, attractions: List[Attraction], 
                          category: str = None, 
                          min_rating: float = 0,
                          max_distance: float = float('inf')) -> List[Attraction]:
        """筛选景点"""
        filtered = attractions
        
        if category:
            filtered = [a for a in filtered if category in a.category]
        
        if min_rating > 0:
            filtered = [a for a in filtered if a.rating >= min_rating]
        
        if max_distance < float('inf'):
            filtered = [a for a in filtered if a.distance <= max_distance]
        
        # 按评分和距离排序
        filtered.sort(key=lambda x: (-x.rating, x.distance))
        
        return filtered

    def stream_attraction_guide(self, user_input: str):
        """流式返回景点讲解内容"""
        try:
            # 增强用户输入，添加更多上下文
            enhanced_input = f"""
            作为专业的景点讲解员，请用{self.current_style}风格详细介绍用户询问的景点。
            
            用户请求：{user_input}
            
            请严格按照Markdown格式要求回答，确保：
            1. 使用清晰的标题层级（# ## ###）
            2. 列表项目单独成行，使用 - 开头
            3. 重要信息使用 **粗体** 标记
            4. 每个部分之间有适当的空行分隔
            5. 确保内容详实、准确、格式规范
            
            请严格按照系统提示中的输出格式要求来组织内容。
            """
            
            # 调用AI模型
            response = self.chain.invoke({
                "input": enhanced_input,
                "history": self.memory.load_memory_variables({})["history"]
            })
            
            # 保存到记忆
            self.memory.save_context(
                {"input": user_input},
                {"output": response}
            )
            
            # 优化流式输出，按句子分割而不是单词
            sentences = response.replace('\n\n', '\n').split('\n')
            for sentence in sentences:
                if sentence.strip():
                    yield sentence + '\n'
                    time.sleep(0.03)  # 减少延迟，提升体验
                else:
                    yield '\n'
                    time.sleep(0.01)
                
        except Exception as e:
            error_message = f"抱歉，在处理您的请求时出现了错误：{str(e)}"
            print(f"景点讲解错误: {e}")
            yield error_message

# 全局变量存储用户的导游智能体实例
user_tour_guide_agents = {}

def get_tour_guide_agent(email: str) -> EnhancedTourGuideAgent:
    """获取或创建用户的导游智能体实例"""
    if email not in user_tour_guide_agents:
        user_tour_guide_agents[email] = EnhancedTourGuideAgent()
    return user_tour_guide_agents[email]

def clear_tour_guide_agents(email: str):
    """清除用户的导游智能体实例"""
    if email in user_tour_guide_agents:
        del user_tour_guide_agents[email]

def get_attraction_guide_response_stream(user_message: str, email: str):
    """获取景点讲解的流式响应"""
    agent = get_tour_guide_agent(email)
    return agent.stream_attraction_guide(user_message)
