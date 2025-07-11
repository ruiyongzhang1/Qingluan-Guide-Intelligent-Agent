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
            budget_per_person: parseInt(document.getElementById('budget_per_person').value),
            travelers: parseInt(document.getElementById('travelers').value),
            accommodation_type: document.getElementById('accommodation_type').value,
            preferences: Array.from(document.querySelectorAll('#preferences .preference-tag.selected')).map(tag => tag.dataset.value),
            transportation_mode: Array.from(document.querySelectorAll('#transportation .preference-tag.selected')).map(tag => tag.dataset.value),
            dietary_restrictions: Array.from(document.querySelectorAll('#dietary_restrictions .preference-tag.selected')).map(tag => tag.dataset.value)
        };
        
        // 验证必填字段
        if (!formData.source || !formData.destination || !formData.start_date || !formData.end_date || !formData.budget_per_person || !formData.travelers || !formData.accommodation_type) {
            alert('请填写所有必填信息！');
            return;
        }
        
        // 验证旅行人数
        if (formData.travelers < 1 || formData.travelers > 20) {
            alert('旅行人数必须在1-20人之间！');
            return;
        }
        
        // 验证人均预算合理性
        if (formData.budget_per_person < 500) {
            if (!confirm(`人均预算仅为 ${formData.budget_per_person} 元，可能无法提供高质量的旅行方案。是否继续？`)) {
                return;
            }
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
    
    // 添加预算显示更新监听器
    const budgetInput = document.getElementById('budget_per_person');
    const travelersSelect = document.getElementById('travelers');
    
    if (budgetInput && travelersSelect) {
        budgetInput.addEventListener('input', updateBudgetDisplay);
        travelersSelect.addEventListener('change', updateBudgetDisplay);
        
        // 初始化显示
        updateBudgetDisplay();
    }
});

// 格式化旅行请求
function formatTravelRequest(formData) {
    const totalBudget = formData.budget_per_person * formData.travelers;
    return `🧳 **旅行规划请求**

**基本信息：**
- 📍 出发地：${formData.source}
- 🎯 目的地：${formData.destination}  
- 📅 旅行日期：${formData.start_date} 至 ${formData.end_date}
- 👥 旅行人数：${formData.travelers} 人
- 💰 人均预算：${formData.budget_per_person} 人民币（总预算约 ${totalBudget} 人民币）
- 🏨 住宿偏好：${formData.accommodation_type}

**旅行偏好：** ${formData.preferences.join(', ')}
**交通方式：** ${formData.transportation_mode.join(', ')}
**饮食要求：** ${formData.dietary_restrictions.join(', ')}`;
}

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
    console.log('Starting travel planning with data:', formData);
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
                    
                    console.log('Travel planning completed, response length:', responseText.length);
                    return;
                }
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            console.log('Travel planning chunk received:', data);
                            
                            if (data.chunk) {
                                responseText += data.chunk;
                                contentDiv.innerHTML = marked.parse(responseText);
                                contentDiv.scrollTop = contentDiv.scrollHeight;
                            } else if (data.error) {
                                console.error('Travel planning error:', data.error);
                                contentDiv.innerHTML = `<div style="color: red;">错误: ${data.error}</div>`;
                                isPlanning = false;
                                planButton.innerHTML = '✨ 重新制定计划';
                                planButton.disabled = false;
                                planButton.classList.remove('loading');
                                return;
                            } else if (data.done) {
                                console.log('Travel planning stream completed');
                                return;
                            }
                        } catch (e) {
                            console.error('解析旅行规划数据出错:', e, line);
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
                if (done) {
                    console.log('Travel message stream completed, response length:', responseText.length);
                    return;
                }
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            console.log('Travel message chunk received:', data);
                            
                            if (data.chunk) {
                                responseText += data.chunk;
                                contentDiv.innerHTML = marked.parse(responseText);
                                contentDiv.scrollTop = contentDiv.scrollHeight;
                            } else if (data.error) {
                                console.error('Travel message error:', data.error);
                                contentDiv.innerHTML = `<div style="color: red;">错误: ${data.error}</div>`;
                                return;
                            } else if (data.done) {
                                console.log('Travel message stream completed');
                                return;
                            }
                        } catch (e) {
                            console.error('解析旅行消息数据出错:', e, line);
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

// 动态计算总预算
function updateBudgetDisplay() {
    const budgetInput = document.getElementById('budget_per_person');
    const travelersSelect = document.getElementById('travelers');
    const budgetLabel = budgetInput.parentElement.querySelector('.form-label');
    
    if (budgetInput.value && travelersSelect.value) {
        const budgetPerPerson = parseInt(budgetInput.value);
        const travelers = parseInt(travelersSelect.value);
        const totalBudget = budgetPerPerson * travelers;
        
        budgetLabel.innerHTML = `人均预算（人民币）<span style="color: #666; font-size: 0.9em;">  总预算约 ${totalBudget} 元</span>`;
    } else {
        budgetLabel.textContent = '人均预算（人民币）';
    }
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
