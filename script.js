const BASE_URL = "http://127.0.0.1:8000"; // FastAPI backend
console.log("✅ Script loaded at: ", new Date().toISOString());

window.addEventListener('beforeunload', (e) => {
    console.log("🚨 Page is about to reload at: ", new Date().toISOString());
});

let currentUser = null;

// Escape HTML to prevent XSS
function escapeHTML(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

function showModal(id) {
    document.querySelectorAll('.overlay').forEach(el => el.classList.remove('active'));
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('active');
        if (id === 'loginModal') document.getElementById('loginPassword').value = '';
        if (id === 'signupModal') document.getElementById('signupForm').reset();
    }
}

function updateAuthUI() {
    const authBtn = document.getElementById('authBtn');
    if (!authBtn) return;

    if (currentUser) {
        authBtn.textContent = currentUser.name;
        authBtn.onclick = () => {
            const confirmed = confirm(`Logged in as ${currentUser.name}. Click OK to log out.`);
            if (confirmed) {
                currentUser = null;
                localStorage.removeItem('currentUser');
                updateAuthUI();
                document.getElementById('history-list').innerHTML = '<p class="placeholder">Log in to save and view your chat history.</p>';
            }
        };
    } else {
        authBtn.textContent = "🔐 Login / Signup";
        authBtn.onclick = () => showModal('loginModal');
    }
}

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', () => {
    // Load saved user
    const saved = localStorage.getItem('currentUser');
    if (saved) {
        try { 
            currentUser = JSON.parse(saved); 
        } catch { 
            localStorage.removeItem('currentUser'); 
        }
    }

    updateAuthUI();

    // Attach form handlers
    document.getElementById('loginForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleLogin(e);
    });

    document.getElementById('signupForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSignup(e);
    });

    // Prevent Enter key in chat input
    document.getElementById('consolebot-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('consolebot-send').click();
        }
    });

    // Expose modal helpers
    window.closeModal = closeModal;
    window.showModal = showModal;
});

// Login Handler
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    if (!email || !password) return alert('Please fill in all fields');

    try {
        const res = await fetch(`${BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Invalid credentials");
        }
        const data = await res.json();
        currentUser = { name: data.user.name, email: data.user.email };
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        closeModal('loginModal');
        updateAuthUI();
        loadChatHistory();
        console.log(`🎉 Logged in as ${currentUser.name}!`);
    } catch (err) {
        alert('❌ ' + err.message);
    }
}

// Signup Handler
async function handleSignup(e) {
    e.preventDefault();
    const name = document.getElementById('signupName').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value.trim();
    if (!name || !email || !password) return alert('Please fill in all fields');

    try {
        const res = await fetch(`${BASE_URL}/auth/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "User already exists");
        }
        const data = await res.json();
        currentUser = { name, email };
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        closeModal('signupModal');
        updateAuthUI();
        saveChat("Welcome!", { explanation: "You're all set. Start coding!", code: "" }, "welcome");
        console.log(`✅ ${data.msg} Welcome, ${name}!`);
    } catch (err) {
        alert('❌ ' + err.message);
    }
}

// Language Mapping
const langConfigs = {
    python: { mode: 'python', name: 'Python', ext: 'py' },
    javascript: { mode: 'javascript', name: 'JavaScript', ext: 'js' },
    java: { mode: 'text/x-java', name: 'Java', ext: 'java' },
    cpp: { mode: 'text/x-c++src', name: 'C++', ext: 'cpp' },
    html: { mode: 'htmlmixed', name: 'HTML', ext: 'html' },
    go: { mode: 'go', name: 'Go', ext: 'go' }
};

// CodeMirror Editor
const editor = CodeMirror(document.getElementById("editor"), {
    lineNumbers: true,
    mode: "python",
    theme: "dracula",
    indentUnit: 2,
    smartIndent: true,
    tabSize: 2,
    indentWithTabs: false,
    lineWrapping: true,
    autofocus: true,
    autoCloseBrackets: true,
    matchBrackets: true
});

// Language Switcher
document.getElementById('language-select').onchange = function () {
    const lang = this.value;
    const config = langConfigs[lang];
    editor.setOption("mode", config.mode);
    document.getElementById('file-name').textContent = `main.${config.ext}`;
};

// Selection Tools
editor.on('cursorActivity', () => {
    const selectedText = editor.getSelection();
    document.getElementById('selection-tools').classList.toggle('hidden', !(selectedText && selectedText.length > 5));
});

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        tab.classList.add('active');
        const tabId = tab.getAttribute('data-tab');
        document.getElementById(tabId).classList.remove('hidden');
        if (tabId === 'history' && currentUser) loadChatHistory();
    });
});

// Call AI
async function callAI(feature, code, lang = 'python', query = null, source_lang = null, target_lang = null) {
    let url, body;

    if (feature === "translate") {
        url = `${BASE_URL}/ai/translate`;
        body = { code, source_lang, target_lang };
    } else if (feature === "generate") {
        url = `${BASE_URL}/ai/generate`;
        body = { query: query || "Write a function", lang };
    } else if (feature === "chat") {
        url = `${BASE_URL}/ai/chat`;
        body = { query, code: code || "", lang };
    } else {
        url = `${BASE_URL}/ai/${feature}`;
        body = { code, lang, query: query || "" };
    }

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Request failed");
        }

        const data = await res.json();
        return data.response || data;
    } catch (err) {
        console.error(`AI call failed [${feature}]`, err);
        return { explanation: `❌ ${err.message}`, code: "" };
    }
}

// Save chat
function saveChat(query, response, feature = "custom") {
    if (!currentUser) return;
    fetch(`${BASE_URL}/history/save/${currentUser.email}/${feature}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            query,
            response: response,
            lang: document.getElementById('language-select').value
        })
    }).catch(console.error);
}

// Load history
async function loadChatHistory() {
    if (!currentUser) return;
    const list = document.getElementById('history-list');
    try {
        const res = await fetch(`${BASE_URL}/history/${currentUser.email}`);
        if (!res.ok) throw new Error("Failed to load");
        const history = await res.json();

        if (!history || history.length === 0) {
            list.innerHTML = '<p class="placeholder">No saved chats yet.</p>';
            return;
        }

        list.innerHTML = '';
        history.slice(0, 20).forEach(chat => {
            const item = document.createElement('div');
            item.className = 'history-item';
            const qText = chat.query || '';
            const query = qText.length > 60 ? qText.substring(0, 60) + '...' : qText;
            item.innerHTML = `<strong>${escapeHTML(query)}</strong><br><small>${new Date(chat.timestamp || Date.now()).toLocaleString()}</small>`;
            item.onclick = () => {
                document.querySelector('[data-tab="consolebot"]').click();
                const messagesDiv = document.getElementById('consolebot-messages');
                const resp = chat.response || {};
                const explanation = (resp.explanation || '').replace(/\n/g, '<br>');
                const codeBlock = resp.code ? `
                    <pre style="background:#242438; padding:0.5rem; border-radius:6px; overflow:auto; margin-top:0.5rem; font-family: 'Fira Code', monospace;">
                        <code>${escapeHTML(resp.code)}</code>
                    </pre>` : '';
                const historyItem = document.createElement('div');
                historyItem.innerHTML = `
                    <p><strong>You:</strong> ${escapeHTML(chat.query || '')}</p>
                    <p><strong>ConsoleBot:</strong>
                        <div><b>Explanation:</b><br>${explanation}</div>
                        ${codeBlock}
                    </p>`;
                messagesDiv.appendChild(historyItem);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            };
            list.appendChild(item);
        });
    } catch (err) {
        list.innerHTML = '<p class="placeholder">Failed to load history.</p>';
    }
}

// Append to ConsoleBot
function appendToConsoleBot(userMsg, aiResponse) {
    const messagesDiv = document.getElementById('consolebot-messages');
    document.querySelector('[data-tab="consolebot"]').click();

    const chatGroup = document.createElement('div');
    const safeUserMsg = escapeHTML(userMsg);

    let aiHtml = '';
    if (typeof aiResponse === 'string') {
        aiHtml = `<p><strong>ConsoleBot:</strong> ${escapeHTML(aiResponse)}</p>`;
    } else {
        aiHtml = `
            <p><strong>ConsoleBot:</strong>
                <div><b>Explanation:</b><br>${(aiResponse.explanation || '').replace(/\n/g, '<br>')}</div>
                ${aiResponse.code ? `
                <pre style="background:#242438; padding:0.5rem; border-radius:6px; overflow:auto; margin-top:0.5rem; font-family: 'Fira Code', monospace;">
                    <code>${escapeHTML(aiResponse.code)}</code>
                </pre>` : ''}
            </p>`;
    }

    chatGroup.innerHTML = `
        <p><strong>You:</strong> ${safeUserMsg}</p>
        ${aiHtml}
    `;

    messagesDiv.appendChild(chatGroup);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}