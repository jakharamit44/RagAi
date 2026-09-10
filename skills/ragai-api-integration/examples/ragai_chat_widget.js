/**
 * RagAi Universal Embeddable Chat Widget
 * Integrates into any Student Portal, Employee Intranet, or Faculty Dashboard.
 * Usage:
 *   <script src="ragai_chat_widget.js"
 *           data-api-base="http://localhost:8000"
 *           data-api-key="ragai_student_default"
 *           data-role="student"
 *           data-department="Computer Science"
 *           data-title="RagAi Campus Copilot"></script>
 */

(function() {
  const currentScript = document.currentScript || (function() {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const CONFIG = {
    apiBase: currentScript.getAttribute('data-api-base') || 'http://localhost:8000',
    apiKey: currentScript.getAttribute('data-api-key') || 'ragai_student_default',
    role: currentScript.getAttribute('data-role') || 'general',
    department: currentScript.getAttribute('data-department') || '',
    title: currentScript.getAttribute('data-title') || 'RagAi Institutional Copilot'
  };

  let sessionId = null;

  // Create Container
  const container = document.createElement('div');
  container.id = 'ragai-widget-root';
  document.body.appendChild(container);

  // Inject Styles
  const style = document.createElement('style');
  style.textContent = `
    #ragai-widget-root {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
    }
    .ragai-bubble-btn {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      color: white;
      border: none;
      box-shadow: 0 10px 25px rgba(37, 99, 235, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .ragai-bubble-btn:hover {
      transform: scale(1.08);
      box-shadow: 0 14px 30px rgba(37, 99, 235, 0.5);
    }
    .ragai-chat-window {
      display: none;
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 400px;
      max-width: calc(100vw - 48px);
      height: 580px;
      max-height: calc(100vh - 120px);
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
      border: 1px solid #e2e8f0;
      flex-direction: column;
      overflow: hidden;
      animation: ragaiFadeIn 0.25s ease-out;
    }
    @keyframes ragaiFadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .ragai-header {
      background: linear-gradient(135deg, #1e293b, #0f172a);
      color: white;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .ragai-header-title {
      font-weight: 600;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .ragai-role-badge {
      font-size: 10px;
      background: rgba(255, 255, 255, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .ragai-close-btn {
      background: none;
      border: none;
      color: #94a3b8;
      font-size: 20px;
      cursor: pointer;
    }
    .ragai-close-btn:hover { color: white; }
    .ragai-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f8fafc;
    }
    .ragai-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13.5px;
      line-height: 1.5;
    }
    .ragai-msg-user {
      align-self: flex-end;
      background: #2563eb;
      color: white;
      border-bottom-right-radius: 2px;
    }
    .ragai-msg-ai {
      align-self: flex-start;
      background: white;
      color: #1e293b;
      border: 1px solid #e2e8f0;
      border-bottom-left-radius: 2px;
    }
    .ragai-citations {
      margin-top: 8px;
      font-size: 11px;
      color: #64748b;
      border-top: 1px solid #f1f5f9;
      padding-top: 6px;
    }
    .ragai-citation-badge {
      display: inline-block;
      background: #e2e8f0;
      padding: 2px 6px;
      border-radius: 4px;
      margin: 2px 4px 2px 0;
      font-size: 10.5px;
    }
    .ragai-input-area {
      padding: 12px;
      background: white;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
    }
    .ragai-input-area input {
      flex: 1;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 13.5px;
      outline: none;
    }
    .ragai-input-area input:focus {
      border-color: #2563eb;
    }
    .ragai-send-btn {
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 0 16px;
      cursor: pointer;
      font-weight: 500;
    }
    .ragai-send-btn:hover { background: #1d4ed8; }
  `;
  document.head.appendChild(style);

  // Widget Markup
  container.innerHTML = `
    <button class="ragai-bubble-btn" id="ragai-toggle-btn" title="Open AI Assistant">💬</button>
    <div class="ragai-chat-window" id="ragai-window">
      <div class="ragai-header">
        <div class="ragai-header-title">
          <span>${CONFIG.title}</span>
          <span class="ragai-role-badge">${CONFIG.role}</span>
        </div>
        <button class="ragai-close-btn" id="ragai-close-btn">&times;</button>
      </div>
      <div class="ragai-messages" id="ragai-msg-list">
        <div class="ragai-msg ragai-msg-ai">
          Hello! I am your verified institutional AI copilot. How can I assist you today?
        </div>
      </div>
      <div class="ragai-input-area">
        <input type="text" id="ragai-input" placeholder="Type your question..." autocomplete="off">
        <button class="ragai-send-btn" id="ragai-submit-btn">Send</button>
      </div>
    </div>
  `;

  // UI Event Handlers
  const toggleBtn = document.getElementById('ragai-toggle-btn');
  const chatWindow = document.getElementById('ragai-window');
  const closeBtn = document.getElementById('ragai-close-btn');
  const msgList = document.getElementById('ragai-msg-list');
  const inputEl = document.getElementById('ragai-input');
  const submitBtn = document.getElementById('ragai-submit-btn');

  function toggleChat() {
    const isVisible = chatWindow.style.display === 'flex';
    chatWindow.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) inputEl.focus();
  }

  toggleBtn.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', () => chatWindow.style.display = 'none');

  async function handleSend() {
    const query = inputEl.value.trim();
    if (!query) return;

    // Append User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'ragai-msg ragai-msg-user';
    userDiv.textContent = query;
    msgList.appendChild(userDiv);
    inputEl.value = '';
    msgList.scrollTop = msgList.scrollHeight;

    // Append Loading indicator
    const aiDiv = document.createElement('div');
    aiDiv.className = 'ragai-msg ragai-msg-ai';
    aiDiv.textContent = 'Thinking...';
    msgList.appendChild(aiDiv);
    msgList.scrollTop = msgList.scrollHeight;

    try {
      const response = await fetch(`${CONFIG.apiBase}/api/v1/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': CONFIG.apiKey
        },
        body: JSON.stringify({
          query: query,
          department: CONFIG.department || null,
          role: CONFIG.role,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      sessionId = data.session_id || sessionId;

      // Render Answer
      aiDiv.innerHTML = data.answer.replace(/\n/g, '<br>');

      // Render Citations if present
      if (data.citations && data.citations.length > 0) {
        const citDiv = document.createElement('div');
        citDiv.className = 'ragai-citations';
        citDiv.innerHTML = '<strong>Verified Sources:</strong><br>';
        data.citations.forEach(c => {
          const b = document.createElement('span');
          b.className = 'ragai-citation-badge';
          b.textContent = `📄 ${c.document_name} (p.${c.page_number})`;
          citDiv.appendChild(b);
        });
        aiDiv.appendChild(citDiv);
      }

    } catch (err) {
      aiDiv.textContent = `Error: ${err.message}. Please check connection or API key.`;
      aiDiv.style.color = '#dc2626';
    }

    msgList.scrollTop = msgList.scrollHeight;
  }

  submitBtn.addEventListener('click', handleSend);
  inputEl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
  });

})();
