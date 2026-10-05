/**
 * Daniel John Britto - AI Text Chatbot Controller
 * STRICTLY TEXT ONLY:
 * - Powered by Google Gemini and resume-grounded RAG.
 * - Written text messaging only.
 * - No microphone, no speech recognition, no speech synthesis.
 * - Completely silent and independent from the AI Voice Assistant.
 */

(() => {
    'use strict';

    // DOM Elements
    const wrapper = document.getElementById('daniel-ai-chatbot');
    const toggleBtn = document.getElementById('chatbot-toggle-btn');
    const windowPanel = document.getElementById('chatbot-window');
    const closeBtn = document.getElementById('chatbot-close-btn');
    const resetBtn = document.getElementById('chatbot-reset-btn');
    const messagesContainer = document.getElementById('chatbot-messages');
    const chipsContainer = document.getElementById('chatbot-chips');
    const typingIndicator = document.getElementById('chatbot-typing');
    const form = document.getElementById('chatbot-form');
    const input = document.getElementById('chatbot-input');
    const sendBtn = document.getElementById('chatbot-send-btn');

    if (!wrapper || !toggleBtn || !windowPanel) {
        return;
    }

    // State Variables (Text Only)
    let isChatOpen = false;
    let chatHistory = []; // [{role: 'user'|'model', text: '...'}]

    /* --------------------------------------------------------------------------
       1. CSRF Token Helper
       -------------------------------------------------------------------------- */
    function getCsrfToken() {
        const tokenInput = form ? form.querySelector('[name=csrfmiddlewaretoken]') : null;
        if (tokenInput && tokenInput.value) return tokenInput.value;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    /* --------------------------------------------------------------------------
       2. Window Toggle & Accessibility
       -------------------------------------------------------------------------- */
    function openChat() {
        isChatOpen = true;
        windowPanel.removeAttribute('hidden');
        windowPanel.classList.add('is-open');
        toggleBtn.classList.add('is-active');
        toggleBtn.setAttribute('aria-expanded', 'true');
        scrollToBottom();
        setTimeout(() => {
            if (input) input.focus();
        }, 150);
    }

    function closeChat() {
        isChatOpen = false;
        windowPanel.classList.remove('is-open');
        toggleBtn.classList.remove('is-active');
        toggleBtn.setAttribute('aria-expanded', 'false');
        setTimeout(() => {
            if (!isChatOpen) {
                windowPanel.setAttribute('hidden', '');
            }
        }, 300);
    }

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isChatOpen) {
            closeChat();
        } else {
            openChat();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeChat();
        });
    }

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isChatOpen) {
            closeChat();
        }
    });

    // Prevent double-click inside chatbot from bubbling to document (so user selecting text doesn't trigger voice assistant)
    windowPanel.addEventListener('dblclick', (e) => {
        e.stopPropagation();
    });
    toggleBtn.addEventListener('dblclick', (e) => {
        e.stopPropagation();
    });

    /* --------------------------------------------------------------------------
       3. Messages UI Helpers
       -------------------------------------------------------------------------- */
    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    function getTimeString() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMarkdown(text) {
        let html = escapeHtml(text);
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Bullet list lines
        html = html.replace(/(?:^|\n)[*•-]\s+(.+)/g, '<br>• $1');
        // Numbered list
        html = html.replace(/(?:^|\n)(\d+)\.\s+(.+)/g, '<br>$1. $2');
        // Line breaks
        html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        return html;
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message message-user';
        msgDiv.innerHTML = `
            <div class="message-bubble">
                <p class="message-text">${escapeHtml(text)}</p>
                <span class="message-time">${getTimeString()}</span>
            </div>
        `;
        messagesContainer.insertBefore(msgDiv, typingIndicator);
        scrollToBottom();
    }

    function appendBotMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message message-bot';
        msgDiv.innerHTML = `
            <div class="message-avatar">DJB</div>
            <div class="message-bubble">
                <div class="message-text">${formatMarkdown(text)}</div>
                <span class="message-time">${getTimeString()}</span>
            </div>
        `;
        messagesContainer.insertBefore(msgDiv, typingIndicator);
        scrollToBottom();
    }

    function showTyping() {
        if (typingIndicator) {
            typingIndicator.removeAttribute('hidden');
            scrollToBottom();
        }
    }

    function hideTyping() {
        if (typingIndicator) {
            typingIndicator.setAttribute('hidden', '');
        }
    }

    /* --------------------------------------------------------------------------
       4. Text Message Sending
       -------------------------------------------------------------------------- */
    async function sendMessage(messageText) {
        const query = messageText || (input ? input.value.trim() : '');
        if (!query) return;

        if (input) {
            input.value = '';
            input.disabled = true;
        }
        if (sendBtn) sendBtn.disabled = true;

        appendUserMessage(query);

        if (chipsContainer) {
            chipsContainer.style.display = 'none';
        }

        showTyping();

        try {
            const csrfToken = getCsrfToken();
            const response = await fetch('/ai-calling/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    message: query,
                    history: chatHistory.slice(-6)
                })
            });

            hideTyping();

            if (response.ok) {
                const data = await response.json();
                const botAnswer = data.answer || "I don't have verified information regarding that in Daniel's portfolio. Feel free to contact him directly at danieljohnbrittoaj@gmail.com.";
                appendBotMessage(botAnswer);

                chatHistory.push({ role: 'user', text: query });
                chatHistory.push({ role: 'model', text: botAnswer });
            } else if (response.status === 429) {
                appendBotMessage("You're sending questions quickly. Please wait a moment before trying again.");
            } else {
                appendBotMessage("I encountered a temporary connection issue. You can contact Daniel directly at danieljohnbrittoaj@gmail.com.");
            }
        } catch (error) {
            hideTyping();
            console.error('Chatbot error:', error);
            appendBotMessage("Unable to reach the assistant service right now. Please check your network connection.");
        } finally {
            if (input) {
                input.disabled = false;
                input.focus();
            }
            if (sendBtn) sendBtn.disabled = false;
            scrollToBottom();
        }
    }

    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage();
        });
    }

    // Suggested Questions Chips
    const chips = document.querySelectorAll('.chat-chip');
    chips.forEach(chip => {
        chip.addEventListener('click', (e) => {
            e.stopPropagation();
            const question = chip.getAttribute('data-question');
            if (question) {
                sendMessage(question);
            }
        });
    });

    // Reset Chat History
    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            chatHistory = [];
            const msgs = messagesContainer.querySelectorAll('.chat-message:not(:first-child):not(.message-typing)');
            msgs.forEach(m => m.remove());
            if (chipsContainer) {
                chipsContainer.style.display = 'block';
            }
            if (input) {
                input.value = '';
                input.focus();
            }
            scrollToBottom();
        });
    }

})();
