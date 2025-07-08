let isInitialLoad = true;

document.addEventListener('DOMContentLoaded', function () {
     // 获取主要 DOM 元素
    const chatBox = document.getElementById('chat-box');               // 聊天消息容器
    const messageInput = document.getElementById('message-input');     // 输入框
    const sendBtn = document.getElementById('send-btn');               // 发送按钮
    const historyBtn = document.getElementById('history-btn');         // 历史记录按钮
    const historyModal = document.getElementById('history-modal');     // 历史记录弹窗
    const closeHistory = document.getElementById('close-history');     // 关闭弹窗（X）按钮
    const closeHistoryBtn = document.getElementById('close-history-btn'); // 关闭弹窗（底部）按钮
    const clearHistoryBtn = document.getElementById('clear-history');  // 清空历史按钮
    const historyList = document.getElementById('history-list');       // 历史记录列表容器
    const newChatBtn = document.getElementById('new-chat-btn');        // 新建对话按钮
    const email = document.querySelector('.user-info span')?.textContent; // 当前用户邮箱，用于加载和清空历史

    /** 滚动到底部 */
    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    /** 动态调整输入框高度（最多显示 5 行） */
    function adjustTextareaHeight() {
        const maxHeight = 5 * 24;
        messageInput.style.height = 'auto';
        const newHeight = Math.min(messageInput.scrollHeight, maxHeight);
        messageInput.style.height = newHeight + 'px';
    }

    messageInput.addEventListener('input', adjustTextareaHeight);

    /** 添加消息到聊天框 */
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

        if (isUser) {
            messageDiv.textContent = content;
        } else {
            const rawHtml = marked.parse(content);
            const cleanHtml = DOMPurify.sanitize(rawHtml);
            messageDiv.innerHTML = cleanHtml;
            
            // 等待DOM更新后应用代码高亮
            setTimeout(() => {
                // 只对当前消息中的代码块应用高亮
                const codeBlocks = messageDiv.querySelectorAll('pre code');
                codeBlocks.forEach(block => {
                    // 确保代码块有正确的语言类
                    if (!block.className.includes('language-')) {
                        block.className = 'language-javascript';
                    }
                    hljs.highlightElement(block);
                });
                
                // 对行内代码应用高亮
                const inlineCodes = messageDiv.querySelectorAll('code:not(pre code)');
                inlineCodes.forEach(code => {
                    if (!code.className.includes('language-')) {
                        code.className = 'language-javascript';
                    }
                    hljs.highlightElement(code);
                });
                
                // 确保所有代码元素都被正确高亮
                messageDiv.querySelectorAll('code').forEach(code => {
                    if (!code.classList.contains('hljs')) {
                        hljs.highlightElement(code);
                    }
                });
            }, 10);
        }

        chatBox.appendChild(messageDiv);
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        scrollToBottom();
    }

    /** 显示"加载中"动画（聊天中三点式） */
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-container';
        loadingDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        chatBox.appendChild(loadingDiv);
        scrollToBottom();
    }

    /** 移除"加载中"动画 */
    function removeLoading() {
        const loadingDiv = document.querySelector('.loading-container');
        if (loadingDiv) loadingDiv.remove();
    }

    /** 发送消息至后端并处理返回 */
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        // 禁用输入框和发送按钮，防止重复发送
        sendBtn.disabled = true;
        messageInput.disabled = true;

        addMessage(message, true);//显示用户消息
        showLoading();
        messageInput.value = '';
        adjustTextareaHeight();

        try {
            console.log('Sending message:', message); // 调试信息
            const res = await fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }

            removeLoading();
            
            // 创建AI消息容器
            const aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'message ai-message streaming';
            chatBox.appendChild(aiMessageDiv);
            
            // 使用 EventSource 处理 SSE
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let chunkCount = 0; // 调试信息
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('Stream finished, total chunks:', chunkCount); // 调试信息
                    break;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // 保留不完整的事件
                
                for (const line of lines) {
                    if (line.trim() === '') continue;
                    
                    const dataLine = line.split('\n').find(l => l.startsWith('data: '));
                    if (dataLine) {
                        try {
                            const data = JSON.parse(dataLine.slice(6));
                            console.log('Received SSE data:', data); // 调试信息
                            
                            if (data.error) {
                                console.error('Server error:', data.error); // 调试信息
                                aiMessageDiv.innerHTML = `<div style="color: #e74c3c;">Error: ${data.error}</div>`;
                                break;
                            }
                            
                            if (data.chunk) {
                                chunkCount++; // 调试信息
                                console.log(`Chunk ${chunkCount}:`, data.chunk.substring(0, 50) + '...'); // 调试信息
                                
                                // 累积内容 - 修复换行问题
                                let currentContent = aiMessageDiv.innerHTML || '';
                                
                                // 如果是第一个chunk且内容为空，直接使用chunk内容
                                if (chunkCount === 1 && currentContent === '') {
                                    currentContent = data.chunk;
                                } else {
                                    // 检查是否需要添加空格来避免单词连接问题
                                    const lastChar = currentContent.slice(-1);
                                    const firstChar = data.chunk.charAt(0);
                                    
                                    // 更准确地检测是否在代码块中
                                    const codeBlockMatches = currentContent.match(/```/g);
                                    const isInCodeBlock = codeBlockMatches && codeBlockMatches.length % 2 === 1;
                                    
                                    // 在代码块中禁用自动空格添加，避免破坏代码格式
                                    if (!isInCodeBlock && lastChar && firstChar && 
                                        /[a-zA-Z0-9\u4e00-\u9fff]/.test(lastChar) && 
                                        /[a-zA-Z0-9\u4e00-\u9fff]/.test(firstChar) &&
                                        !/\s/.test(lastChar) && !/\s/.test(firstChar)) {
                                        currentContent += ' ' + data.chunk;
                                    } else {
                                        currentContent += data.chunk;
                                    }
                                }
                                
                                // 解析markdown并应用高亮
                                const rawHtml = marked.parse(currentContent);
                                const cleanHtml = DOMPurify.sanitize(rawHtml);
                                aiMessageDiv.innerHTML = cleanHtml;
                                
                                // 应用代码高亮
                                setTimeout(() => {
                                    const codeBlocks = aiMessageDiv.querySelectorAll('pre code');
                                    codeBlocks.forEach(block => {
                                        if (!block.className.includes('language-')) {
                                            block.className = 'language-javascript';
                                        }
                                        hljs.highlightElement(block);
                                    });
                                    
                                    const inlineCodes = aiMessageDiv.querySelectorAll('code:not(pre code)');
                                    inlineCodes.forEach(code => {
                                        if (!code.className.includes('language-')) {
                                            code.className = 'language-javascript';
                                        }
                                        hljs.highlightElement(code);
                                    });
                                }, 0);
                                
                                scrollToBottom();
                            }
                            
                            if (data.done) {
                                console.log('Stream completed'); // 调试信息
                                // 流式输出完成，移除光标效果
                                aiMessageDiv.classList.remove('streaming');
                                break;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e, dataLine);
                        }
                    }
                }
            }
            
            // 移除欢迎消息
            const welcome = document.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            
        } catch (err) {
            console.error('Network error:', err); // 调试信息
            removeLoading();
            addMessage(`Network error: ${err.message}`);
        } finally {
            // 重新启用输入框和发送按钮
            sendBtn.disabled = false;
            messageInput.disabled = false;
        }
    }

    // 回车键发送消息
    messageInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 发送按钮点击事件
    sendBtn.addEventListener('click', sendMessage);

    /** 加载历史记录 */
    function loadHistory() {
        if (!email) return;

        historyList.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">加载中...</div>';

        fetch('/load_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                historyList.innerHTML = `<div style="text-align:center; color:#999; padding:20px;">${data.error}</div>`;
                return;
            }

            if (!data.history || data.history.length === 0) {
                historyList.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">暂无历史记录</div>';
                return;
            }

            historyList.innerHTML = data.history.map((conv, idx) => `
                <div class="history-entry" data-index="${idx}" style="...">
                    <div style="font-weight:bold; margin-bottom:10px;">对话 ${idx + 1} - ${conv.date}</div>
                    <div style="line-height:1.6; max-height:100px; overflow-y:auto; font-size:0.9rem;">
                        ${conv.messages.slice(0, 2).map(msg => `
                            <div style="margin-bottom:6px; padding:6px; border-radius:6px; ${msg.is_user ? 'background-color:#e3f2fd;' : 'background-color:#f1f8e9;'}">
                                ${msg.is_user ? '你：' : '青鸾：'} ${msg.text}
                            </div>
                        `).join('')}
                        ${conv.messages.length > 2 ? `<div style="color:#666; font-size:0.85rem;">+ ${conv.messages.length - 2} 条消息...</div>` : ''}
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.history-entry').forEach((el, i) => {
                el.addEventListener('click', () => {
                    const selected = data.history[i];
                    chatBox.innerHTML = '';
                    selected.messages.forEach(msg => {
                        addMessage(msg.text, msg.is_user);
                    });
                    historyModal.style.display = 'none';
                    
                    // 确保历史记录中的代码也能正确高亮
                    setTimeout(() => {
                        const codeBlocks = chatBox.querySelectorAll('pre code');
                        codeBlocks.forEach(block => {
                            if (!block.className.includes('language-')) {
                                block.className = 'language-javascript';
                            }
                            hljs.highlightElement(block);
                        });
                        
                        const inlineCodes = chatBox.querySelectorAll('code:not(pre code)');
                        inlineCodes.forEach(code => {
                            if (!code.className.includes('language-')) {
                                code.className = 'language-javascript';
                            }
                            hljs.highlightElement(code);
                        });
                        
                        // 确保所有代码元素都被正确高亮
                        chatBox.querySelectorAll('code').forEach(code => {
                            if (!code.classList.contains('hljs')) {
                                hljs.highlightElement(code);
                            }
                        });
                    }, 100);
                });
            });
        })
        .catch(err => {
            historyList.innerHTML = `<div style="text-align:center; color:#e74c3c; padding:20px;">加载失败：${err.message}</div>`;
        });
    }

    /** 初始化需求表单并渲染 */
    function initRequirementsForm() {
        chatBox.innerHTML = '';

        const welcome = document.createElement('div');
        welcome.className = 'welcome-message';
        welcome.innerHTML = '<p>👋👋 欢迎来到青鸾向导!请先填写您的需求表格，以便我们为您提供更精准的服务</p>';
        chatBox.appendChild(welcome);

        const requirementsDiv = document.createElement('div');
        requirementsDiv.id = 'requirements-container';
        requirementsDiv.className = 'requirements-container';

        requirementsDiv.innerHTML = `
        <div class="requirements-header">旅行需求表</div>
            <form id="requirements-form" class="requirements-form">
                  <!-- 新增：出发地点 -->
                 <!-- 出发地点 -->
                    <div class="req-form-group">
                        <label for="source"><i class="fas fa-map-marker-alt"></i> 出发地点</label>
                        <input type="text" id="source" name="source" placeholder="例如：上海、广州" required>
                    </div>
                    
                    <!-- 目的地 -->
                    <div class="req-form-group">
                        <label for="destination"><i class="fas fa-location-dot"></i> 目的地</label>
                        <input type="text" id="destination" name="destination" placeholder="例如：北京、海南岛" required>
                    </div>
                    
                    <div class="req-form-group req-full-width">
                        <label><i class="far fa-calendar"></i> 旅行日期</label>
                        <div class="date-group">
                            <div class="date-input-container">
                                <label for="start-date" style="font-weight: normal; font-size: 14px; margin-bottom: 5px;">开始日期</label>
                                <input type="date" id="start-date" name="start_date" required>
                            </div>
                            <div class="date-input-container">
                                <label for="end-date" style="font-weight: normal; font-size: 14px; margin-bottom: 5px;">结束日期</label>
                                <input type="date" id="end-date" name="end_date" required>
                            </div>
                        </div>
                        <div class="date-info">
                            <i class="fas fa-info-circle"></i>
                            <span id="date-range-info">默认设置为今天开始的行程</span>
                        </div>
                    </div>

                    <div class="req-form-group">
                        <label for="people">出行人数</label>
                        <input
                            type="number"
                            id="people"
                            name="people"
                            placeholder="请输入旅行总人数"
                            min="1"
                            required
                        >
                    </div>
                    <!-- 预算 -->
                    <div class="req-form-group">
                        <label for="budget"><i class="fas fa-wallet"></i> 预算</label>
                        <div style="display: flex; align-items: center;">
                            <input type="number" id="budget" name="budget" placeholder="请输入预算金额" min="1" required">
                        </div>
                    </div>
                    
                    <!-- 旅行偏好 -->
                    <div class="req-form-group">
                        <label for="preferences"><i class="fas fa-heart"></i> 旅行偏好</label>
                        <select id="preferences" name="preferences" required>
                            <option value="">请选择</option>
                            <option value="自然风光">自然风光</option>
                            <option value="历史文化">历史文化</option>
                            <option value="美食体验">美食体验</option>
                            <option value="购物娱乐">购物娱乐</option>
                            <option value="休闲度假">休闲度假</option>
                            <option value="探险活动">探险活动</option>
                        </select>
                    </div>
                    
                    <!-- 住宿类型偏好 -->
                    <div class="req-form-group">
                        <label for="accommodation_type"><i class="fas fa-bed"></i> 住宿类型偏好</label>
                        <select id="accommodation_type" name="accommodation_type" required>
                            <option value="">请选择</option>
                            <option value="经济型酒店">经济型酒店</option>
                            <option value="舒适型酒店">舒适型酒店</option>
                            <option value="豪华酒店">豪华酒店</option>
                            <option value="民宿">民宿</option>
                            <option value="度假村">度假村</option>
                        </select>
                    </div>
                    
                    <!-- 交通方式偏好 -->
                    <div class="req-form-group">
                        <label for="transportation_mode"><i class="fas fa-car"></i> 交通方式偏好</label>
                        <select id="transportation_mode" name="transportation_mode" required>
                            <option value="">请选择</option>
                            <option value="公共交通">公共交通</option>
                            <option value="租车自驾">租车自驾</option>
                            <option value="包车服务">包车服务</option>
                            <option value="步行和自行车">步行和自行车</option>
                        </select>
                    </div>
                    
                    <!-- 饮食限制 -->
                    <div class="req-form-group req-full-width">
                        <label for="dietary_restrictions"><i class="fas fa-utensils"></i> 饮食限制</label>
                        <input type="text" id="dietary_restrictions" name="dietary_restrictions" placeholder="例如：素食、无麸质、过敏食物等">
                    </div>
                
                                <div class="req-form-group req-full-width" style="text-align: center;">
                    <button type="submit" class="submit-btn">提交需求并开始聊天</button>
                </div>
            </form>
            
            <div class="requirements-note">
                * 提交需求后，我们会根据您的需求生成个性化的旅行建议
            </div>`;
        chatBox.appendChild(requirementsDiv);

        // 设置默认日期为明后两天
        const today = new Date();
        const startDate = new Date(today);
        const endDate = new Date(today);
        startDate.setDate(today.getDate() + 1);
        endDate.setDate(today.getDate() + 2);

        document.getElementById('start-date').valueAsDate = startDate;
        document.getElementById('end-date').valueAsDate = endDate;

        document.getElementById('requirements-form').addEventListener('submit', handleRequirementsSubmit);
        scrollToBottom();
    }

    /** 提交需求表单逻辑 */
    function handleRequirementsSubmit(e) {
        e.preventDefault();

        const submitBtn = document.querySelector('#requirements-form .submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="btn-spinner"></span> 处理中...';

        const formData = {
            source: document.getElementById('source').value,
            destination: document.getElementById('destination').value,
            start_date: document.getElementById('start-date').value,
            end_date: document.getElementById('end-date').value,
            people: document.getElementById('people').value,
            budget: document.getElementById('budget').value,
            preferences: document.getElementById('preferences').value,
            accommodation_type: document.getElementById('accommodation_type').value,
            transportation_mode: document.getElementById('transportation_mode').value,
            dietary_restrictions: document.getElementById('dietary_restrictions').value || '无',
            timestamp: new Date().toISOString()
        };

        const userMessage = `旅行需求：\n出发地：${formData.source}\n目的地：${formData.destination}\n出发日期：${formData.start_date}\n返回日期：${formData.end_date}\n出行人数：${formData.people}\n预算：${formData.budget}\n旅行偏好：${formData.preferences}\n住宿类型偏好：${formData.accommodation_type}\n交通方式偏好：${formData.transportation_mode}\n饮食限制：${formData.dietary_restrictions}`;

        showLoading();

        fetch('/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userMessage,
                formData: formData
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            removeLoading();
            
            // 隐藏表单
            const formContainer = document.getElementById('requirements-container');
            if (formContainer) formContainer.style.display = 'none';
            
            // 创建AI消息容器
            const aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'message ai-message streaming';
            chatBox.appendChild(aiMessageDiv);
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let chunkCount = 0; // 添加chunk计数器
            
            return new Promise((resolve, reject) => {
                function readStream() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            resolve();
                            return;
                        }
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n\n');
                        buffer = lines.pop();
                        
                        for (const line of lines) {
                            if (line.trim() === '') continue;
                            
                            const dataLine = line.split('\n').find(l => l.startsWith('data: '));
                            if (dataLine) {
                                try {
                                    const data = JSON.parse(dataLine.slice(6));
                                    
                                    if (data.error) {
                                        aiMessageDiv.innerHTML = `<div style="color: #e74c3c;">需求提交失败: ${data.error}</div>`;
                                        reject(new Error(data.error));
                                        return;
                                    }
                                    
                                    if (data.chunk) {
                                        chunkCount++; // 增加chunk计数
                                        // 累积内容 - 修复换行问题
                                        let currentContent = aiMessageDiv.innerHTML || '';
                                        
                                        // 如果是第一个chunk且内容为空，直接使用chunk内容
                                        if (chunkCount === 1 && currentContent === '') {
                                            currentContent = data.chunk;
                                        } else {
                                            // 检查是否需要添加空格来避免单词连接问题
                                            const lastChar = currentContent.slice(-1);
                                            const firstChar = data.chunk.charAt(0);
                                            
                                            // 更准确地检测是否在代码块中
                                            const codeBlockMatches = currentContent.match(/```/g);
                                            const isInCodeBlock = codeBlockMatches && codeBlockMatches.length % 2 === 1;
                                            
                                            // 在代码块中禁用自动空格添加，避免破坏代码格式
                                            if (!isInCodeBlock && lastChar && firstChar && 
                                                /[a-zA-Z0-9\u4e00-\u9fff]/.test(lastChar) && 
                                                /[a-zA-Z0-9\u4e00-\u9fff]/.test(firstChar) &&
                                                !/\s/.test(lastChar) && !/\s/.test(firstChar)) {
                                                currentContent += ' ' + data.chunk;
                                            } else {
                                                currentContent += data.chunk;
                                            }
                                        }
                                        
                                        // 解析markdown并应用高亮
                                        const rawHtml = marked.parse(currentContent);
                                        const cleanHtml = DOMPurify.sanitize(rawHtml);
                                        aiMessageDiv.innerHTML = cleanHtml;
                                        
                                        // 应用代码高亮
                                        setTimeout(() => {
                                            const codeBlocks = aiMessageDiv.querySelectorAll('pre code');
                                            codeBlocks.forEach(block => {
                                                if (!block.className.includes('language-')) {
                                                    block.className = 'language-javascript';
                                                }
                                                hljs.highlightElement(block);
                                            });
                                            
                                            const inlineCodes = aiMessageDiv.querySelectorAll('code:not(pre code)');
                                            inlineCodes.forEach(code => {
                                                if (!code.className.includes('language-')) {
                                                    code.className = 'language-javascript';
                                                }
                                                hljs.highlightElement(code);
                                            });
                                        }, 0);
                                        
                                        scrollToBottom();
                                    }
                                    
                                    if (data.done) {
                                        aiMessageDiv.classList.remove('streaming');
                                        resolve();
                                        return;
                                    }
                                } catch (e) {
                                    console.error('Error parsing SSE data:', e, dataLine);
                                }
                            }
                        }
                        
                        readStream();
                    }).catch(reject);
                }
                
                readStream();
            });
        })
        .catch(error => {
            removeLoading();
            addMessage('网络错误: ' + error.message, false);
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '提交需求并开始聊天';
        });
    }

    /** 历史记录相关事件绑定 */
    if (historyBtn) {
        historyBtn.addEventListener('click', () => {
            historyModal.style.display = 'flex';
            loadHistory();
        });
    }

    if (closeHistory) {
        closeHistory.addEventListener('click', () => {
            historyModal.style.display = 'none';
        });
    }

    if (closeHistoryBtn) {
        closeHistoryBtn.addEventListener('click', () => {
            historyModal.style.display = 'none';
        });
    }

    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            if (!email || !confirm('确定要清除所有历史记录吗？此操作不可撤销。')) return;

            fetch('/clear_history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert('历史记录已清除');
                    historyList.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">历史记录已清空</div>';
                } else {
                    alert('清除失败：' + data.error);
                }
            })
            .catch(err => alert('网络错误：' + err.message));
        });
    }

    /** 新建对话：初始化表单并通知服务器 */
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            fetch('/new_conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(() => {
                initRequirementsForm();
            })
            .catch(err => console.error('Error creating new conversation:', err));
        });
    }

    /** 页面初次加载显示表单 */
    initRequirementsForm();
    // 初始化时滚动到底
    scrollToBottom();
});
