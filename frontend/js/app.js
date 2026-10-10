/**
 * Enterprise Agentic Document Intelligence Client
 * Pure Vanilla JavaScript ES6+
 */
(function () {
    'use strict';

    // Application State
    const state = {
        apiBaseUrl: localStorage.getItem('agentic_rag_api_url') || '/api/v1',
        tenantId: localStorage.getItem('agentic_rag_tenant_id') || 'tenant-default',
        authToken: localStorage.getItem('agentic_rag_auth_token') || '',
        activeConversationId: null,
        conversations: [],
        documents: [],
        pollingTimer: null,
        isSendingMessage: false
    };

    // DOM Elements
    const dom = {
        sidebar: document.getElementById('sidebar'),
        btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
        btnNewChat: document.getElementById('btn-new-chat'),
        btnRefreshDocs: document.getElementById('btn-refresh-docs'),
        btnUploadTrigger: document.getElementById('btn-upload-trigger'),
        btnCloseUploadModal: document.getElementById('btn-close-upload-modal'),
        uploadModal: document.getElementById('upload-modal'),
        dropZone: document.getElementById('drop-zone'),
        fileInput: document.getElementById('file-input'),
        uploadProgressContainer: document.getElementById('upload-progress-container'),
        uploadingFileName: document.getElementById('uploading-file-name'),
        uploadProgressBar: document.getElementById('upload-progress-bar'),
        uploadPercent: document.getElementById('upload-percent'),
        uploadStatusText: document.getElementById('upload-status-text'),
        btnOpenSettings: document.getElementById('btn-open-settings'),
        btnCloseSettingsModal: document.getElementById('btn-close-settings-modal'),
        settingsModal: document.getElementById('settings-modal'),
        inputApiUrl: document.getElementById('input-api-url'),
        inputTenantId: document.getElementById('input-tenant-id'),
        inputAuthToken: document.getElementById('input-auth-token'),
        btnSaveSettings: document.getElementById('btn-save-settings'),
        currentTenantDisplay: document.getElementById('current-tenant-id'),
        documentList: document.getElementById('document-list'),
        docsEmptyState: document.getElementById('docs-empty-state'),
        conversationList: document.getElementById('conversation-list'),
        convosEmptyState: document.getElementById('convos-empty-state'),
        chatContainer: document.getElementById('chat-container'),
        chatMessages: document.getElementById('chat-messages'),
        welcomeHero: document.getElementById('welcome-hero'),
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        btnSendMessage: document.getElementById('btn-send-message'),
        conversationTitle: document.getElementById('conversation-title'),
        toastContainer: document.getElementById('toast-container')
    };

    // --- Helper & Utility Functions ---

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        dom.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function getHeaders(custom = {}) {
        const headers = {
            'X-Tenant-ID': state.tenantId,
            ...custom
        };
        if (state.authToken) {
            headers['Authorization'] = `Bearer ${state.authToken}`;
        }
        return headers;
    }

    function formatBytes(bytes, decimals = 1) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /**
     * Escape HTML entities to prevent XSS from model responses or user input
     */
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Safe lightweight Markdown parser
     * Converts markdown bold, code blocks, lists without raw HTML injection
     */
    function renderSafeMarkdown(rawText) {
        if (!rawText) return '';
        const escaped = escapeHtml(rawText);

        // Code blocks: ```lang ... ```
        let formatted = escaped.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
        });

        // Inline code: `code`
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold: **text**
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic: *text*
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Paragraphs and newlines
        const paragraphs = formatted.split(/\n\s*\n/).map(p => {
            p = p.trim();
            if (!p) return '';
            if (p.startsWith('<pre>')) return p;
            
            // Check for list items
            if (p.includes('\n- ') || p.startsWith('- ')) {
                const lines = p.split('\n');
                let inList = false;
                let listHtml = '';
                lines.forEach(line => {
                    const trimmed = line.trim();
                    if (trimmed.startsWith('- ')) {
                        if (!inList) { listHtml += '<ul>'; inList = true; }
                        listHtml += `<li>${trimmed.substring(2)}</li>`;
                    } else {
                        if (inList) { listHtml += '</ul>'; inList = false; }
                        listHtml += `<p>${trimmed}</p>`;
                    }
                });
                if (inList) listHtml += '</ul>';
                return listHtml;
            }

            return `<p>${p.replace(/\n/g, '<br>')}</p>`;
        });

        return paragraphs.join('');
    }

    // --- API Interactions ---

    async function fetchDocuments() {
        try {
            const res = await fetch(`${state.apiBaseUrl}/documents`, {
                headers: getHeaders()
            });
            if (!res.ok) {
                if (res.status === 404) return;
                throw new Error(`Error ${res.status}: ${res.statusText}`);
            }
            const data = await res.json();
            state.documents = data.documents || [];
            renderDocuments();

            // Check if any document is queued or processing
            const hasPending = state.documents.some(d => d.status === 'QUEUED' || d.status === 'PROCESSING');
            if (hasPending && !state.pollingTimer) {
                state.pollingTimer = setInterval(fetchDocuments, 3000);
            } else if (!hasPending && state.pollingTimer) {
                clearInterval(state.pollingTimer);
                state.pollingTimer = null;
            }
        } catch (err) {
            console.warn('Failed to load documents:', err);
        }
    }

    async function fetchConversations() {
        try {
            const res = await fetch(`${state.apiBaseUrl}/conversations`, {
                headers: getHeaders()
            });
            if (!res.ok) return;
            const data = await res.json();
            state.conversations = data.conversations || [];
            renderConversations();
        } catch (err) {
            console.warn('Failed to load conversations:', err);
        }
    }

    async function loadConversationMessages(convoId) {
        try {
            state.activeConversationId = convoId;
            renderConversations(); // update active class

            const res = await fetch(`${state.apiBaseUrl}/conversations/${convoId}`, {
                headers: getHeaders()
            });
            if (!res.ok) throw new Error('Could not fetch conversation history');
            const data = await res.json();
            
            dom.conversationTitle.textContent = data.title || 'Conversation History';
            dom.chatMessages.innerHTML = '';
            if (dom.welcomeHero) dom.welcomeHero.classList.add('hidden');

            (data.messages || []).forEach(msg => {
                appendMessageToUI(msg.role, msg.content, msg.citations, msg.created_at);
            });

            scrollChatToBottom();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }

    async function uploadDocument(file) {
        if (!file) return;
        const validExtensions = ['.pdf', '.txt'];
        const fileName = file.name.toLowerCase();
        const isValid = validExtensions.some(ext => fileName.endsWith(ext));
        if (!isValid) {
            showToast('Unsupported format. Please upload a PDF or TXT file.', 'error');
            return;
        }

        const maxBytes = 25 * 1024 * 1024; // 25 MB
        if (file.size > maxBytes) {
            showToast('File size exceeds the 25 MB limit.', 'error');
            return;
        }

        // Show UI progress
        dom.uploadProgressContainer.classList.remove('hidden');
        dom.uploadingFileName.textContent = file.name;
        dom.uploadProgressBar.style.width = '30%';
        dom.uploadPercent.textContent = '30%';
        dom.uploadStatusText.textContent = 'Uploading to ingestion service...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${state.apiBaseUrl}/documents`, {
                method: 'POST',
                headers: getHeaders(),
                body: formData
            });

            if (!res.ok) {
                const errJson = await res.json().catch(() => ({ detail: 'Upload failed' }));
                throw new Error(errJson.detail || `Upload failed with status ${res.status}`);
            }

            dom.uploadProgressBar.style.width = '100%';
            dom.uploadPercent.textContent = '100%';
            dom.uploadStatusText.textContent = 'Queued for processing!';
            
            showToast(`Document "${file.name}" uploaded successfully`, 'success');
            setTimeout(() => {
                closeUploadModal();
                fetchDocuments();
            }, 1000);
        } catch (err) {
            dom.uploadStatusText.textContent = `Error: ${err.message}`;
            dom.uploadStatusText.style.color = 'var(--danger)';
            showToast(err.message, 'error');
        }
    }

    async function deleteDocument(docId, event) {
        event.stopPropagation();
        if (!confirm('Are you sure you want to delete this document and its chunk embeddings?')) {
            return;
        }
        try {
            const res = await fetch(`${state.apiBaseUrl}/documents/${docId}`, {
                method: 'DELETE',
                headers: getHeaders()
            });
            if (!res.ok) throw new Error('Deletion failed');
            showToast('Document deleted successfully', 'success');
            fetchDocuments();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }

    async function sendMessage(question) {
        if (!question || state.isSendingMessage) return;
        state.isSendingMessage = true;
        dom.btnSendMessage.disabled = true;

        if (dom.welcomeHero) {
            dom.welcomeHero.classList.add('hidden');
        }

        // Render User Message
        appendMessageToUI('user', question);
        dom.chatInput.value = '';
        dom.chatInput.style.height = 'auto';

        // Render Typing Indicator for Assistant
        const loadingIndicator = createLoadingIndicator();
        dom.chatMessages.appendChild(loadingIndicator);
        scrollChatToBottom();

        try {
            const payload = {
                message: question,
                conversation_id: state.activeConversationId
            };

            const res = await fetch(`${state.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: getHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify(payload)
            });

            loadingIndicator.remove();

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: 'Failed to generate response' }));
                throw new Error(errData.detail || `Server error ${res.status}`);
            }

            const data = await res.json();
            state.activeConversationId = data.conversation_id;

            appendMessageToUI('assistant', data.answer, data.citations, new Date().toISOString(), data.meta);
            fetchConversations();
        } catch (err) {
            loadingIndicator.remove();
            appendMessageToUI('assistant', `⚠️ **Error:** ${err.message}`);
            showToast(err.message, 'error');
        } finally {
            state.isSendingMessage = false;
            dom.btnSendMessage.disabled = false;
            dom.chatInput.focus();
            scrollChatToBottom();
        }
    }

    // --- UI Rendering ---

    function renderDocuments() {
        if (!state.documents || state.documents.length === 0) {
            dom.documentList.innerHTML = '<div class="empty-state-small">No documents uploaded yet</div>';
            return;
        }

        dom.documentList.innerHTML = '';
        state.documents.forEach(doc => {
            const card = document.createElement('div');
            card.className = 'doc-card';
            
            const statusClass = (doc.status || 'queued').toLowerCase();
            const chunkInfo = doc.chunk_count !== undefined ? `${doc.chunk_count} chunks` : '';
            const sizeInfo = formatBytes(doc.file_size);

            card.innerHTML = `
                <div class="doc-header-row">
                    <span class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                    <button class="doc-delete-btn icon-button" title="Delete document">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
                <div class="doc-meta-row">
                    <span class="status-badge ${statusClass}">${escapeHtml(doc.status)}</span>
                    <span>${sizeInfo} ${chunkInfo ? `&bull; ${chunkInfo}` : ''}</span>
                </div>
            `;

            const delBtn = card.querySelector('.doc-delete-btn');
            delBtn.addEventListener('click', (e) => deleteDocument(doc.id, e));
            dom.documentList.appendChild(card);
        });
    }

    function renderConversations() {
        if (!state.conversations || state.conversations.length === 0) {
            dom.conversationList.innerHTML = '<div class="empty-state-small">No prior conversations</div>';
            return;
        }

        dom.conversationList.innerHTML = '';
        state.conversations.forEach(c => {
            const item = document.createElement('div');
            const isActive = c.id === state.activeConversationId;
            item.className = `convo-item ${isActive ? 'active' : ''}`;
            item.textContent = c.title || 'Untitled Conversation';
            item.addEventListener('click', () => loadConversationMessages(c.id));
            dom.conversationList.appendChild(item);
        });
    }

    function appendMessageToUI(role, text, citations = [], timestamp = null, meta = null) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = renderSafeMarkdown(text);
        bubble.appendChild(content);

        // Citations rendering
        if (citations && citations.length > 0) {
            const citationsBox = document.createElement('div');
            citationsBox.className = 'citations-box';
            
            const citeHeader = document.createElement('div');
            citeHeader.className = 'citations-header';
            citeHeader.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                Verified Sources (${citations.length})
            `;
            citationsBox.appendChild(citeHeader);

            const chipsContainer = document.createElement('div');
            chipsContainer.className = 'citation-chips';

            citations.forEach(cite => {
                const chip = document.createElement('div');
                chip.className = 'citation-chip';
                const pageLabel = cite.page_number ? `Page ${cite.page_number}` : 'Full Text';
                const chunkLabel = cite.chunk_index !== undefined ? `Chunk #${cite.chunk_index}` : '';
                chip.innerHTML = `
                    <span class="cite-title">${escapeHtml(cite.document_name || 'Document')}</span>
                    <span class="cite-meta">${pageLabel} ${chunkLabel ? `&bull; ${chunkLabel}` : ''}</span>
                    ${cite.snippet ? `<span class="cite-snippet" title="${escapeHtml(cite.snippet)}">"${escapeHtml(cite.snippet)}"</span>` : ''}
                `;
                chipsContainer.appendChild(chip);
            });

            citationsBox.appendChild(chipsContainer);
            bubble.appendChild(citationsBox);
        }

        // Meta info (latency, tokens)
        if (meta) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            const parts = [];
            if (meta.latency_ms) parts.push(`${meta.latency_ms} ms`);
            if (meta.tokens_used) parts.push(`${meta.tokens_used} tokens`);
            if (meta.model_id) parts.push(meta.model_id);
            if (parts.length > 0) {
                metaDiv.textContent = parts.join(' • ');
                bubble.appendChild(metaDiv);
            }
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        dom.chatMessages.appendChild(row);
        scrollChatToBottom();
    }

    function createLoadingIndicator() {
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.id = 'loading-indicator-row';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'AI';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;

        bubble.appendChild(typing);
        row.appendChild(avatar);
        row.appendChild(bubble);
        return row;
    }

    function scrollChatToBottom() {
        dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
    }

    function openUploadModal() {
        dom.uploadModal.classList.remove('hidden');
        dom.uploadProgressContainer.classList.add('hidden');
        dom.fileInput.value = '';
    }

    function closeUploadModal() {
        dom.uploadModal.classList.add('hidden');
    }

    function openSettingsModal() {
        dom.inputApiUrl.value = state.apiBaseUrl;
        dom.inputTenantId.value = state.tenantId;
        dom.inputAuthToken.value = state.authToken;
        dom.settingsModal.classList.remove('hidden');
    }

    function closeSettingsModal() {
        dom.settingsModal.classList.add('hidden');
    }

    function saveSettings() {
        const newApi = dom.inputApiUrl.value.trim() || '/api/v1';
        const newTenant = dom.inputTenantId.value.trim() || 'tenant-default';
        const newAuth = dom.inputAuthToken.value.trim();

        state.apiBaseUrl = newApi;
        state.tenantId = newTenant;
        state.authToken = newAuth;

        localStorage.setItem('agentic_rag_api_url', newApi);
        localStorage.setItem('agentic_rag_tenant_id', newTenant);
        localStorage.setItem('agentic_rag_auth_token', newAuth);

        dom.currentTenantDisplay.textContent = newTenant;
        closeSettingsModal();
        showToast('Settings saved successfully', 'success');

        fetchDocuments();
        fetchConversations();
    }

    function startNewChat() {
        state.activeConversationId = null;
        renderConversations();
        dom.conversationTitle.textContent = 'Knowledge Workspace';
        dom.chatMessages.innerHTML = '';
        if (dom.welcomeHero) {
            dom.welcomeHero.classList.remove('hidden');
            dom.chatMessages.appendChild(dom.welcomeHero);
        }
        dom.chatInput.focus();
    }

    // --- Event Listeners Setup ---

    function setupEventListeners() {
        // Toggle mobile sidebar
        if (dom.btnToggleSidebar) {
            dom.btnToggleSidebar.addEventListener('click', () => {
                dom.sidebar.classList.toggle('open');
            });
        }

        // New Chat
        dom.btnNewChat.addEventListener('click', startNewChat);

        // Refresh docs
        dom.btnRefreshDocs.addEventListener('click', fetchDocuments);

        // Upload triggers
        dom.btnUploadTrigger.addEventListener('click', openUploadModal);
        dom.btnCloseUploadModal.addEventListener('click', closeUploadModal);

        // Drag and Drop
        dom.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dom.dropZone.classList.add('dragover');
        });
        dom.dropZone.addEventListener('dragleave', () => {
            dom.dropZone.classList.remove('dragover');
        });
        dom.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dom.dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                uploadDocument(e.dataTransfer.files[0]);
            }
        });
        dom.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadDocument(e.target.files[0]);
            }
        });

        // Settings Modal
        dom.btnOpenSettings.addEventListener('click', openSettingsModal);
        dom.btnCloseSettingsModal.addEventListener('click', closeSettingsModal);
        dom.btnSaveSettings.addEventListener('click', saveSettings);

        // Auto-expand textarea
        dom.chatInput.addEventListener('input', () => {
            dom.chatInput.style.height = 'auto';
            dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 140) + 'px';
        });

        // Enter key to send (Shift+Enter for newline)
        dom.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                dom.chatForm.dispatchEvent(new Event('submit'));
            }
        });

        // Chat Form Submit
        dom.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = dom.chatInput.value.trim();
            if (text) sendMessage(text);
        });

        // Close modal on background click
        window.addEventListener('click', (e) => {
            if (e.target === dom.uploadModal) closeUploadModal();
            if (e.target === dom.settingsModal) closeSettingsModal();
        });
    }

    // --- Init ---
    function init() {
        dom.currentTenantDisplay.textContent = state.tenantId;
        setupEventListeners();
        fetchDocuments();
        fetchConversations();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
