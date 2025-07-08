// 旅行页面专用JavaScript

let currentPlan = null;
let isPlanning = false;

// 处理偏好标签选择
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.preference-tags').forEach(container => {
        container.addEventListener('click', function(e) {
            if (e.target.classList.contains('preference-tag')) {
                e.target.classList.toggle('selected');
            }
        });
    });
    
    // 设置最小日期为今天
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('start_date').min = today;
    document.getElementById('end_date').min = today;
    
    // 初始化日期值
    initializeDates();
    
    // 确保结束日期不早于开始日期
    document.getElementById('start_date').addEventListener('change', function() {
        const startDate = this.value;
        document.getElementById('end_date').min = startDate;
        if (document.getElementById('end_date').value < startDate) {
            document.getElementById('end_date').value = startDate;
        }
    });
    
    // 表单提交
    document.getElementById('travelForm').addEventListener('submit', function(e) {
        e.preventDefault();
        if (isPlanning) return;
        
        // 收集表单数据
        const formData = {
            source: document.getElementById('source').value,
            destination: document.getElementById('destination').value,
            start_date: document.getElementById('start_date').value,
            end_date: document.getElementById('end_date').value,
            budget: parseInt(document.getElementById('budget').value),
            accommodation_type: document.getElementById('accommodation_type').value,
            preferences: Array.from(document.querySelectorAll('#preferences .preference-tag.selected')).map(tag => tag.dataset.value),
            transportation_mode: Array.from(document.querySelectorAll('#transportation .preference-tag.selected')).map(tag => tag.dataset.value),
            dietary_restrictions: Array.from(document.querySelectorAll('#dietary_restrictions .preference-tag.selected')).map(tag => tag.dataset.value)
        };
        
        // 验证必填字段
        if (!formData.source || !formData.destination || !formData.start_date || !formData.end_date || !formData.budget || !formData.accommodation_type) {
            alert('请填写所有必填信息！');
            return;
        }
        
        if (formData.preferences.length === 0) {
            alert('请至少选择一个旅行偏好！');
            return;
        }
        
        if (formData.transportation_mode.length === 0) {
            formData.transportation_mode = ['公共交通'];
        }
        
        if (formData.dietary_restrictions.length === 0) {
            formData.dietary_restrictions = ['无特殊要求'];
        }
        
        startTravelPlanning(formData);
    });
    
    // 回车发送消息
    document.getElementById('message-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});

// 初始化日期值
function initializeDates() {
    const today = new Date();
    const startDate = new Date(today);
    const endDate = new Date(today);
    
    // 出发日期设置为明天
    startDate.setDate(today.getDate() + 1);
    
    // 返回日期设置为出发日期后7天
    endDate.setDate(startDate.getDate() + 7);
    
    // 格式化日期为 YYYY-MM-DD
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };
    
    // 设置初始值
    document.getElementById('start_date').value = formatDate(startDate);
    document.getElementById('end_date').value = formatDate(endDate);
}

// 开始旅行规划
function startTravelPlanning(formData) {
    isPlanning = true;
    const planButton = document.getElementById('planButton');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    
    // 更新按钮状态 - 添加加载动画
    planButton.innerHTML = '⏳ 正在制定计划...';
    planButton.disabled = true;
    planButton.classList.add('loading');
    
    // 添加用户请求消息
    addMessage(formatTravelRequest(formData), true);
    
    // 添加三点式加载动画
    const loadingMessage = addTypingIndicator();
    
    // 发送规划请求
    fetch('/plan_travel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络错误');
        }
        
        // 移除三点式加载动画
        loadingMessage.remove();
        
        // 创建响应消息容器
        const responseDiv = addMessage('', false);
        const contentDiv = responseDiv.querySelector('.message-content');
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let responseText = '';
        
        function readStream() {
            reader.read().then(({done, value}) => {
                if (done) {
                    currentPlan = responseText;
                    isPlanning = false;
                    
                    // 恢复按钮状态 - 移除加载动画
                    planButton.innerHTML = '✨ 重新制定计划';
                    planButton.disabled = false;
                    planButton.classList.remove('loading');
                    
                    // 启用聊天输入
                    messageInput.disabled = false;
                    sendBtn.disabled = false;
                    messageInput.placeholder = '对计划有疑问？随时问我！';
                    
                    return;
                }
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.chunk) {
                                responseText += data.chunk;
                                contentDiv.innerHTML = marked.parse(responseText);
                                contentDiv.scrollTop = contentDiv.scrollHeight;
                            } else if (data.error) {
                                contentDiv.innerHTML = `<div style="color: red;">错误: ${data.error}</div>`;
                                isPlanning = false;
                                planButton.innerHTML = '✨ 重新制定计划';
                                planButton.disabled = false;
                                planButton.classList.remove('loading');
                                return;
                            }
                        } catch (e) {
                            console.log('解析数据出错:', e);
                        }
                    }
                }
                
                readStream();
            });
        }
        
        readStream();
    })
    .catch(error => {
        console.error('规划出错:', error);
        loadingMessage.remove();
        addMessage(`<div style="color: red;">规划过程中出现错误: ${error.message}</div>`, false);
        isPlanning = false;
        planButton.innerHTML = '✨ 重新制定计划';
        planButton.disabled = false;
        planButton.classList.remove('loading');
    });
}

// 格式化旅行请求
function formatTravelRequest(formData) {
    return `🧳 **旅行规划请求**

**基本信息：**
- 📍 出发地：${formData.source}
- 🎯 目的地：${formData.destination}  
- 📅 旅行日期：${formData.start_date} 至 ${formData.end_date}
- 💰 预算：$${formData.budget} 美元
- 🏨 住宿偏好：${formData.accommodation_type}

**旅行偏好：** ${formData.preferences.join(', ')}
**交通方式：** ${formData.transportation_mode.join(', ')}
**饮食要求：** ${formData.dietary_restrictions.join(', ')}`;
}

// 快速提问
function askQuickQuestion(question) {
    if (!currentPlan) {
        alert('请先制定旅行计划！');
        return;
    }
    
    document.getElementById('message-input').value = question;
    sendMessage();
}

// 添加三点式加载动画
function addTypingIndicator() {
    const chatBox = document.getElementById('chat-box');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return typingDiv;
}

// 发送消息
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message || isPlanning) return;
    
    messageInput.value = '';
    addMessage(message, true);
    
    // 添加三点式加载动画
    const loadingMessage = addTypingIndicator();
    
    fetch('/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            agent_type: 'travel'
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络错误');
        }
        
        // 移除加载消息
        loadingMessage.remove();
        
        // 创建响应消息容器
        const responseDiv = addMessage('', false);
        const contentDiv = responseDiv.querySelector('.message-content');
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let responseText = '';
        
        function readStream() {
            reader.read().then(({done, value}) => {
                if (done) return;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.chunk) {
                                responseText += data.chunk;
                                contentDiv.innerHTML = marked.parse(responseText);
                                contentDiv.scrollTop = contentDiv.scrollHeight;
                            } else if (data.error) {
                                contentDiv.innerHTML = `<div style="color: red;">错误: ${data.error}</div>`;
                                return;
                            }
                        } catch (e) {
                            console.log('解析数据出错:', e);
                        }
                    }
                }
                
                readStream();
            });
        }
        
        readStream();
    })
    .catch(error => {
        console.error('发送消息出错:', error);
        loadingMessage.remove();
        addMessage(`<div style="color: red;">发送失败: ${error.message}</div>`, false);
    });
}

// 添加消息到聊天区域
function addMessage(content, isUser) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'user-message' : 'ai-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isUser) {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.innerHTML = content;
    }
    
    messageDiv.appendChild(contentDiv);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    return messageDiv;
} 