/**
 * ============================================================================
 * Daniel's AI Voice Assistant — Session-Based Lifecycle Architecture
 * ============================================================================
 * Strict session state model:
 *   IDLE -> START -> LISTENING -> 2s Silence -> PROCESSING -> SPEAKING -> IDLE
 *
 * At ANY point during an active session:
 *   STOP -> HARD STOP ALL RECOGNITION, TIMERS, NETWORK, AUDIO -> IDLE
 *
 * Stale callback protection:
 *   Every session has an incrementing sessionId. Any asynchronous callback
 *   belonging to an old session is immediately ignored.
 * ============================================================================
 */

(function () {
    'use strict';

    // ──────────────────────────────────────────────────
    //  DOM Elements
    // ──────────────────────────────────────────────────
    const hudContainer    = document.getElementById('portfolio-voice-assistant');
    const hudPill         = document.getElementById('va-hud-pill');
    const hudStatusText   = document.getElementById('va-hud-status-text');
    const hudMiniWave     = document.getElementById('va-hud-mini-wave');
    const hudCard         = document.getElementById('va-hud-card');
    const hudStateLabel   = document.getElementById('va-hud-state-label');
    const hudSpeaker      = document.getElementById('va-hud-speaker');
    const hudTranscript   = document.getElementById('va-hud-transcript');
    const replayBtn       = document.getElementById('va-replay-btn');
    const sessionBtn      = document.getElementById('va-session-btn') || document.getElementById('va-stop-btn');

    // Send & Try Again button area elements (Manual fallback)
    const sendArea        = document.getElementById('va-hud-send-area');
    const sendInput       = document.getElementById('va-hud-send-input');
    const sendBtn         = document.getElementById('va-send-btn');
    const tryAgainBtn     = document.getElementById('va-try-again-btn');

    if (!hudContainer) return;

    // ──────────────────────────────────────────────────
    //  Explicit State Model
    // ──────────────────────────────────────────────────
    const AssistantState = {
        IDLE:       'idle',
        LISTENING:  'listening',
        PROCESSING: 'processing',
        SPEAKING:   'speaking',
        STOPPED:    'stopped'
    };

    let currentState          = AssistantState.IDLE;
    let voiceSessionActive    = false;
    let intentionalStop       = true;
    let shouldRestartOnEnd    = false;
    let recognitionErrorHandled = false;   // true when onerror already decided the next action
    let currentSessionId      = 0;
    let activeFetchController = null;

    let recognition           = null;
    let currentAudio          = null;
    let synth                 = window.speechSynthesis || null;
    let availableVoices       = [];
    let selectedVoice         = null;
    let currentUtterance      = null;
    let lastSpokenAnswer      = '';
    let lastAudioUrl          = '';
    let voiceHistory          = [];

    // Debounce management
    let lastToggleTime        = 0;
    let pendingStartTimeout   = null;
    let needsSessionIncrement = true;  // false when stop already advanced currentSessionId

    // 2-Second Silence Detection Variables
    const SILENCE_WAIT_MS     = 2000;
    let silenceTimer          = null;
    let accumulatedTranscript = '';
    let currentInterimText    = '';
    let hasSpokenThisSession  = false;
    let isFinalizing          = false;

    // Preferred language detection
    function getPreferredLanguage() {
        const navLang = (navigator.languages && navigator.languages[0]) || navigator.language || 'en-IN';
        if (navLang.startsWith('en')) {
            if (navLang === 'en' || navLang === 'en-') {
                return 'en-IN';
            }
            return navLang;
        }
        return 'en-IN';
    }

    // ======================================================================
    //  Primary Session Action Button UI Synchronizer
    //  [Start Voice] when idle/stopped | [Stop] when active
    // ======================================================================
    function updateSessionButton(isActive) {
        if (!sessionBtn) return;
        if (isActive) {
            sessionBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                </svg>
                <span>Stop</span>
            `;
            sessionBtn.title = 'Stop voice session';
            sessionBtn.className = 'va-hud-btn va-hud-btn-stop';
        } else {
            sessionBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="5 3 19 12 5 21 5 3" fill="currentColor"></polygon>
                </svg>
                <span>Start Voice</span>
            `;
            sessionBtn.title = 'Start new voice session';
            sessionBtn.className = 'va-hud-btn va-hud-btn-start';
        }
    }

    // ======================================================================
    //  Centralized UI State Synchronizer
    // ======================================================================
    function updateUIForState(state) {
        currentState = state;

        hudContainer.classList.remove('is-listening', 'is-speaking', 'is-ready', 'is-inactive', 'is-active');

        switch (state) {
            case AssistantState.IDLE:
                hudContainer.classList.add('is-inactive');
                if (hudCard) hudCard.setAttribute('hidden', '');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Click Start Voice or double-click to speak';
                if (hudStateLabel) hudStateLabel.textContent = 'Voice Assistant (Idle)';
                if (hudSpeaker) hudSpeaker.textContent = 'Status';
                if (hudTranscript) hudTranscript.textContent = 'Click Start Voice or double-click anywhere to talk to Daniel.';
                updateSessionButton(false);
                hideSendArea();
                break;

            case AssistantState.LISTENING:
                hudContainer.classList.add('is-active', 'is-listening');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.removeAttribute('hidden');
                if (hudStatusText) hudStatusText.textContent = 'Listening... (Speak now)';
                if (hudStateLabel) hudStateLabel.textContent = 'Listening to your voice...';
                if (hudSpeaker) hudSpeaker.textContent = 'You (Speaking)';
                if (!accumulatedTranscript && hudTranscript) {
                    hudTranscript.textContent = 'Listening... Speak your question about Daniel.';
                }
                updateSessionButton(true);
                hideSendArea();
                break;

            case AssistantState.PROCESSING:
                hudContainer.classList.add('is-active');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Thinking... (Click Stop to cancel)';
                if (hudStateLabel) hudStateLabel.textContent = 'Thinking with Gemini AI...';
                if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI';
                if (hudTranscript) hudTranscript.textContent = 'Analyzing your question...';
                updateSessionButton(true);
                hideSendArea();
                break;

            case AssistantState.SPEAKING:
                hudContainer.classList.add('is-active', 'is-speaking');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.removeAttribute('hidden');
                if (hudStatusText) hudStatusText.textContent = 'Daniel is speaking... (Click Stop to interrupt)';
                if (hudStateLabel) hudStateLabel.textContent = 'Daniel AI Spoken Answer';
                if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI';
                updateSessionButton(true);
                hideSendArea();
                break;

            case AssistantState.STOPPED:
                hudContainer.classList.add('is-active');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Voice assistant stopped';
                if (hudStateLabel) hudStateLabel.textContent = 'Voice assistant stopped';
                updateSessionButton(false);
                break;
        }
    }

    // ======================================================================
    //  1. CSRF Token Helper
    // ======================================================================
    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) return decodeURIComponent(match[1]);
        const formToken = document.querySelector('input[name=csrfmiddlewaretoken]');
        return formToken ? formToken.value : '';
    }

    // ======================================================================
    //  2. Speech Synthesis Setup & Voice Loading
    // ======================================================================
    function loadVoices() {
        if (!synth) return;
        availableVoices = synth.getVoices();
        if (availableVoices.length > 0) {
            selectedVoice =
                availableVoices.find(v => v.lang.startsWith('en') &&
                    (v.name.includes('Natural') || v.name.includes('Online') || v.name.includes('Google') || v.name.includes('Neural'))
                ) ||
                availableVoices.find(v => v.lang === 'en-IN') ||
                availableVoices.find(v => v.lang === 'en-US' || v.lang === 'en-GB') ||
                availableVoices.find(v => v.lang.startsWith('en')) ||
                availableVoices[0];
        }
    }

    if (synth) {
        loadVoices();
        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = loadVoices;
        }
    }

    function cleanTextForSpeech(rawText) {
        return rawText
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/[*_#`~]/g, '')
            .replace(/https?:\/\/\S+/g, 'link')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/•/g, '')
            .replace(/\n+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMarkdown(text) {
        if (!text) return '';
        let html = escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/(?:^|\n)[*•-]\s+(.+)/g, '<br>• $1');
        html = html.replace(/(?:^|\n)(\d+)\.\s+(.+)/g, '<br>$1. $2');
        html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        return html;
    }

    // ======================================================================
    //  3. Audio Playback Management
    // ======================================================================
    function stopAllAudio() {
        if (currentAudio) {
            try {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {}
            currentAudio = null;
        }
        if (synth) {
            try {
                synth.cancel();
            } catch (e) {}
        }
        currentUtterance = null;
        hudContainer.classList.remove('is-speaking');
        if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
    }

    function playGeneratedAudio(audioUrl, fallbackText, thisSessionId) {
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
            return;
        }

        stopAllAudio();
        updateUIForState(AssistantState.SPEAKING);
        console.log('[VoiceAssistant] Speech synthesis started');

        if (audioUrl) {
            try {
                const audio = new Audio(audioUrl);
                currentAudio = audio;

                audio.onended = () => { handleSpeechEnded(thisSessionId); };
                audio.onerror = () => {
                    currentAudio = null;
                    playSpeechSynthesisFallback(fallbackText, thisSessionId);
                };

                const playPromise = audio.play();
                if (playPromise !== undefined) {
                    playPromise.catch(() => {
                        currentAudio = null;
                        playSpeechSynthesisFallback(fallbackText, thisSessionId);
                    });
                }
                return;
            } catch (e) {
                currentAudio = null;
            }
        }

        playSpeechSynthesisFallback(fallbackText, thisSessionId);
    }

    function playSpeechSynthesisFallback(text, thisSessionId) {
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
            return;
        }

        stopAllAudio();
        updateUIForState(AssistantState.SPEAKING);
        console.log('[VoiceAssistant] Speech synthesis started');

        if (!synth) { handleSpeechEnded(thisSessionId); return; }

        const clean = cleanTextForSpeech(text);
        if (!clean) { handleSpeechEnded(thisSessionId); return; }

        const utterance = new SpeechSynthesisUtterance(clean);
        currentUtterance = utterance;

        if (selectedVoice) utterance.voice = selectedVoice;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.lang = getPreferredLanguage();

        utterance.onend = () => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }
            handleSpeechEnded(thisSessionId);
        };

        utterance.onerror = (err) => {
            if (err.error !== 'interrupted' && err.error !== 'canceled') {
                console.warn('SpeechSynthesis error:', err);
            }
            if (thisSessionId === currentSessionId && voiceSessionActive) {
                handleSpeechEnded(thisSessionId);
            }
        };

        try {
            synth.speak(utterance);
        } catch (e) {
            handleSpeechEnded(thisSessionId);
        }
    }

    function handleSpeechEnded(thisSessionId) {
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
            return;
        }

        console.log('[VoiceAssistant] Speech synthesis completed');
        hudContainer.classList.remove('is-speaking');
        if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');

        // Session complete: transition to STOPPED without auto-listening
        voiceSessionActive = false;
        updateUIForState(AssistantState.STOPPED);
        if (hudStateLabel) {
            hudStateLabel.textContent = 'Finished answering. Click Start Voice to speak again.';
        }
        console.log('[VoiceAssistant] Returned to IDLE');
    }

    // ======================================================================
    //  4. Manual Send & Try Again Area Management (Fallback)
    // ======================================================================
    function showSendArea(questionText) {
        if (!sendArea || !sendInput || !sendBtn) return;
        sendInput.textContent = questionText;
        sendBtn.disabled = !questionText.trim();
        sendArea.removeAttribute('hidden');
        if (hudTranscript) hudTranscript.textContent = `"${questionText}"`;
    }

    function hideSendArea() {
        if (sendArea) sendArea.setAttribute('hidden', '');
        if (sendInput) sendInput.textContent = '';
        if (sendBtn) sendBtn.disabled = false;
        hudContainer.classList.remove('is-ready');
    }

    function handleSendClick() {
        if (!sendInput || currentState === AssistantState.PROCESSING) return;

        const question = (sendInput.textContent || sendInput.innerText || '').trim();
        if (!question) return;

        if (sendBtn) sendBtn.disabled = true;
        hideSendArea();

        const isCommand = checkVoiceCommand(question);
        if (!isCommand) {
            processSpokenQuery(question, currentSessionId);
        } else {
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    function handleTryAgain() {
        startNewVoiceSession();
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleSendClick();
        });
    }

    if (tryAgainBtn) {
        tryAgainBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleTryAgain();
        });
    }

    if (sendInput) {
        sendInput.addEventListener('input', () => {
            const text = (sendInput.textContent || sendInput.innerText || '').trim();
            if (sendBtn) sendBtn.disabled = !text;
        });

        sendInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendClick();
            }
        });
    }

    // ======================================================================
    //  5. Replay Feature
    // ======================================================================
    function replayLastAnswer() {
        if (!lastSpokenAnswer && !lastAudioUrl) {
            if (hudTranscript) hudTranscript.textContent = "There is no previous answer to replay yet.";
            return;
        }

        console.log('[VoiceAssistant] Replaying previous answer without Gemini call');
        stopListening(true);
        hideSendArea();

        const sessionId = ++currentSessionId;
        needsSessionIncrement = true;  // replay consumed an increment; next start must also increment
        voiceSessionActive = true;
        intentionalStop = false;

        if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI (Replay)';
        if (hudTranscript) hudTranscript.innerHTML = formatMarkdown(lastSpokenAnswer);

        playGeneratedAudio(lastAudioUrl, lastSpokenAnswer, sessionId);
    }

    if (replayBtn) {
        replayBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            replayLastAnswer();
        });
    }

    // ======================================================================
    //  6. Voice Commands Engine
    // ======================================================================
    function checkVoiceCommand(query) {
        const text = query.toLowerCase().replace(/[.,!?;:]/g, '').trim();

        if (['repeat that', 'say it again', 'say that again', 'repeat', 'replay',
             'replay that', 'replay your last answer', 'can you repeat that',
             'one more time'].includes(text)) {
            replayLastAnswer();
            return true;
        }

        if (['stop', 'stop speaking', 'stop talking', 'be quiet', 'pause audio', 'goodbye', 'bye', 'cancel'].includes(text)) {
            stopVoiceSession();
            return true;
        }

        return false;
    }

    // ======================================================================
    //  7. 2-Second Silence Detection
    // ======================================================================
    function clearSilenceTimer() {
        if (silenceTimer) {
            clearTimeout(silenceTimer);
            silenceTimer = null;
        }
    }

    function resetSilenceTimer(thisSessionId) {
        clearSilenceTimer();
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            return;
        }

        const activeSpeech = (accumulatedTranscript + ' ' + currentInterimText).trim();
        if (!activeSpeech) return;

        console.log(`[VoiceAssistant] Silence timer started: ${SILENCE_WAIT_MS}ms`);

        silenceTimer = setTimeout(() => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }
            finalizeAccumulatedSpeech(thisSessionId);
        }, SILENCE_WAIT_MS);
    }

    function finalizeAccumulatedSpeech(thisSessionId) {
        if (isFinalizing) return;
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
            return;
        }

        isFinalizing = true;
        clearSilenceTimer();

        const completeQuery = (accumulatedTranscript + (currentInterimText ? ' ' + currentInterimText : '')).trim();
        currentInterimText = '';

        if (!completeQuery) {
            isFinalizing = false;
            return;
        }

        console.log(`[VoiceAssistant] Final transcript: "${completeQuery}"`);
        console.log('[VoiceAssistant] Question finalized');

        // Stop recognition before calling Gemini
        stopListening(true);
        console.log('[VoiceAssistant] Recognition stopped');

        const isCommand = checkVoiceCommand(completeQuery);
        if (!isCommand) {
            processSpokenQuery(completeQuery, thisSessionId);
        }

        isFinalizing = false;
    }

    // ======================================================================
    //  8. Speech Recognition Lifecycle
    // ======================================================================
    function cleanupRecognition() {
        if (!recognition) return;
        const oldRec = recognition;
        recognition = null;
        try {
            oldRec.onstart = null;
            oldRec.onaudiostart = null;
            oldRec.onaudioend = null;
            oldRec.onsoundstart = null;
            oldRec.onsoundend = null;
            oldRec.onspeechstart = null;
            oldRec.onspeechend = null;
            oldRec.onresult = null;
            oldRec.onerror = null;
            oldRec.onend = null;
            oldRec.stop();
        } catch (e) {
            try { oldRec.abort(); } catch (err) {}
        }
    }

    function createFreshRecognition(thisSessionId) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return null;

        const rec = new SpeechRecognition();
        rec.continuous     = true;
        rec.interimResults = true;
        rec.lang           = getPreferredLanguage();
        rec.maxAlternatives = 1;

        rec.onstart = () => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale onstart for session: ${thisSessionId} (current: ${currentSessionId})`);
                try { rec.abort(); } catch (e) {}
                return;
            }
            console.log(`[VoiceAssistant] Recognition started for session: ${thisSessionId}`);
            updateUIForState(AssistantState.LISTENING);
        };

        // ── Diagnostic handlers: trace Chrome's audio/speech pipeline ──
        rec.onaudiostart = () => {
            console.log(`[VoiceAssistant] Audio capture started (session: ${thisSessionId}, active: ${thisSessionId === currentSessionId})`);
        };
        rec.onaudioend = () => {
            console.log(`[VoiceAssistant] Audio capture ended (session: ${thisSessionId}, active: ${thisSessionId === currentSessionId})`);
        };
        rec.onsoundstart = () => {
            console.log(`[VoiceAssistant] Sound detected (session: ${thisSessionId})`);
        };
        rec.onsoundend = () => {
            console.log(`[VoiceAssistant] Sound ended (session: ${thisSessionId})`);
        };
        rec.onspeechstart = () => {
            console.log(`[VoiceAssistant] Speech detected by browser (session: ${thisSessionId})`);
        };
        rec.onspeechend = () => {
            console.log(`[VoiceAssistant] Speech ended (session: ${thisSessionId})`);
        };

        rec.onresult = (event) => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }

            let sessionFinal = '';
            let sessionInterim = '';

            for (let i = 0; i < event.results.length; i++) {
                const res = event.results[i];
                if (res.isFinal) {
                    sessionFinal += res[0].transcript + ' ';
                } else {
                    sessionInterim += res[0].transcript;
                }
            }

            if (sessionInterim.trim()) {
                currentInterimText = sessionInterim.trim();
            } else {
                currentInterimText = '';
            }

            if (sessionFinal.trim()) {
                accumulatedTranscript = sessionFinal.trim();
            }

            const liveCombined = (accumulatedTranscript + (currentInterimText ? ' ' + currentInterimText : '')).trim();

            if (liveCombined) {
                if (!hasSpokenThisSession) {
                    hasSpokenThisSession = true;
                    console.log('[VoiceAssistant] Speech detected');
                }
                if (hudTranscript) {
                    hudTranscript.textContent = `"${liveCombined}..."`;
                }

                resetSilenceTimer(thisSessionId);
            }
        };

        rec.onerror = (event) => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive || intentionalStop) {
                console.log(`[VoiceAssistant] Ignoring stale onerror (${event.error}) for session: ${thisSessionId} (current: ${currentSessionId}, active: ${voiceSessionActive})`);
                return;
            }

            console.warn(`[VoiceAssistant] Recognition error: ${event.error} (session: ${thisSessionId}, active: ${voiceSessionActive}, state: ${currentState})`);

            if (event.error === 'no-speech') {
                console.log('[VoiceAssistant] No speech detected');
                recognitionErrorHandled = true;
                shouldRestartOnEnd = false;
                stopVoiceSession();
                if (hudTranscript) {
                    hudTranscript.textContent = 'No speech was detected. Click Start Voice or double-click to speak.';
                }
                return;
            }

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                recognitionErrorHandled = true;
                stopVoiceSession();
                if (hudTranscript) {
                    hudTranscript.textContent = 'Microphone permission was denied. Please allow microphone access in your browser.';
                }
                return;
            }

            if (event.error === 'aborted') {
                recognitionErrorHandled = true;
                return;
            }

            recognitionErrorHandled = true;
            stopVoiceSession();
        };

        rec.onend = () => {
            if (thisSessionId !== currentSessionId || !voiceSessionActive || intentionalStop) {
                console.log(`[VoiceAssistant] Ignoring stale onend for session: ${thisSessionId} (current: ${currentSessionId}, active: ${voiceSessionActive}, intentional: ${intentionalStop})`);
                recognitionErrorHandled = false;
                return;
            }
            console.log(`[VoiceAssistant] Recognition ended for session: ${thisSessionId}`);

            // If onerror already handled this cycle, only honour its shouldRestartOnEnd decision
            if (recognitionErrorHandled) {
                recognitionErrorHandled = false;

                if (shouldRestartOnEnd && voiceSessionActive && !intentionalStop) {
                    shouldRestartOnEnd = false;
                    cleanupRecognition();
                    pendingStartTimeout = setTimeout(() => {
                        if (thisSessionId === currentSessionId && voiceSessionActive && !intentionalStop) {
                            startListening(thisSessionId);
                        }
                    }, 300);
                }
                // If shouldRestartOnEnd is false here, onerror already called stopVoiceSession — do nothing.
                return;
            }

            // Recognition ended without an error (e.g. network timeout, service disconnect)
            if (shouldRestartOnEnd && voiceSessionActive && !intentionalStop) {
                shouldRestartOnEnd = false;
                cleanupRecognition();
                pendingStartTimeout = setTimeout(() => {
                    if (thisSessionId === currentSessionId && voiceSessionActive && !intentionalStop) {
                        startListening(thisSessionId);
                    }
                }, 300);
                return;
            }

            // Unexpected end while we were listening — stop gracefully
            if (currentState === AssistantState.LISTENING) {
                stopVoiceSession();
            }
        };

        return rec;
    }

    async function startListening(sessionId) {
        if (!sessionId) sessionId = currentSessionId;
        if (sessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${sessionId}`);
            return;
        }

        console.log(`[VoiceAssistant] Recognition starting for session: ${sessionId}`);

        try {
            cleanupRecognition();

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                stopVoiceSession();
                alert('Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Apple Safari.');
                return;
            }

            recognition = createFreshRecognition(sessionId);
            if (!recognition) return;

            recognition.start();
        } catch (e) {
            console.warn('Recognition start exception:', e);
            if (sessionId === currentSessionId && voiceSessionActive) {
                stopVoiceSession();
            }
        }
    }

    function stopListening(isIntentional = true) {
        clearSilenceTimer();
        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
        shouldRestartOnEnd = false;
        intentionalStop = isIntentional;

        hudContainer.classList.remove('is-listening');
        if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');

        if (recognition) {
            try { recognition.stop(); } catch (e) {
                try { recognition.abort(); } catch (err) {}
            }
        }
    }

    // ======================================================================
    //  9. AI Question Analysis & Answer Generation (Gemini RAG)
    // ======================================================================
    async function processSpokenQuery(question, thisSessionId) {
        if (thisSessionId !== currentSessionId || !voiceSessionActive) {
            console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
            return;
        }

        updateUIForState(AssistantState.PROCESSING);
        stopAllAudio();
        stopListening(true);
        hideSendArea();

        console.log('[VoiceAssistant] Gemini request started');
        activeFetchController = new AbortController();

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
                    message: question,
                    history: voiceHistory.slice(-4)
                }),
                signal: activeFetchController.signal
            });

            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }

            console.log(`[VoiceAssistant] Gemini response received`);

            if (response.ok) {
                const data = await response.json();
                if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                    console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                    return;
                }

                if (data.success === false) {
                    const errorAnswer = data.answer || "The assistant encountered an issue. Please try again.";
                    if (hudTranscript) hudTranscript.innerHTML = formatMarkdown(errorAnswer);
                    playGeneratedAudio('', errorAnswer, thisSessionId);
                } else {
                    const botAnswer = data.answer || "I don't have verified information about that in Daniel's portfolio. You can contact Daniel directly at danieljohnbrittoaj@gmail.com.";
                    const audioUrl = data.audio_url || '';

                    lastSpokenAnswer = botAnswer;
                    lastAudioUrl = audioUrl;
                    voiceHistory.push({ role: 'user', text: question });
                    voiceHistory.push({ role: 'model', text: botAnswer });

                    if (hudTranscript) hudTranscript.innerHTML = formatMarkdown(botAnswer);
                    if (replayBtn) replayBtn.style.display = 'inline-flex';

                    playGeneratedAudio(audioUrl, botAnswer, thisSessionId);
                }
            } else if (response.status === 429) {
                const rateMsg = "You are asking questions very quickly. Please wait a moment before asking again.";
                if (hudTranscript) hudTranscript.textContent = rateMsg;
                playGeneratedAudio('', rateMsg, thisSessionId);
            } else {
                const errMsg = "I encountered a temporary connection issue. You can reach Daniel directly at danieljohnbrittoaj@gmail.com.";
                if (hudTranscript) hudTranscript.textContent = errMsg;
                playGeneratedAudio('', errMsg, thisSessionId);
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                return;
            }
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }
            console.error('[VoiceAssistant] Network error:', err.message || err);
            const netMsg = "Network error connecting to Daniel's voice assistant. Please check your connection.";
            if (hudTranscript) hudTranscript.textContent = netMsg;
            playGeneratedAudio('', netMsg, thisSessionId);
        } finally {
            activeFetchController = null;
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    // ======================================================================
    //  10. Session Lifecycle Controls (Start Voice & Hard Stop)
    // ======================================================================
    function startNewVoiceSession() {
        console.log('[VoiceAssistant] START requested');

        // If stop already advanced currentSessionId, reuse it; otherwise increment
        if (needsSessionIncrement) {
            ++currentSessionId;
        }
        needsSessionIncrement = true; // reset for next cycle
        const sessionId = currentSessionId;
        voiceSessionActive = true;
        intentionalStop = false;
        shouldRestartOnEnd = false;
        recognitionErrorHandled = false;
        accumulatedTranscript = '';
        currentInterimText = '';
        hasSpokenThisSession = false;
        isFinalizing = false;

        console.log(`[VoiceAssistant] New session: ${sessionId}`);

        stopAllAudio();
        clearSilenceTimer();
        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
        if (activeFetchController) { activeFetchController.abort(); activeFetchController = null; }

        cleanupRecognition();
        hideSendArea();

        updateUIForState(AssistantState.LISTENING);
        startListening(sessionId);
    }

    function stopVoiceSession() {
        // Guard: prevent double-stop from incrementing currentSessionId twice
        if (!voiceSessionActive) {
            console.log('[VoiceAssistant] STOP ignored: no active session');
            return;
        }

        console.log('[VoiceAssistant] STOP requested');

        const cancelledId = currentSessionId;
        voiceSessionActive = false;
        intentionalStop = true;
        shouldRestartOnEnd = false;
        recognitionErrorHandled = false;

        // Explicit session invalidation: advance currentSessionId so that
        // any pending async callback from session N sees N !== currentSessionId.
        // startNewVoiceSession() will reuse this new value via needsSessionIncrement.
        currentSessionId++;
        needsSessionIncrement = false; // start will reuse the value stop just set

        console.log(`[VoiceAssistant] Cancelling session: ${cancelledId}`);

        clearSilenceTimer();
        console.log('[VoiceAssistant] Silence timer cleared');

        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
        if (activeFetchController) { activeFetchController.abort(); activeFetchController = null; }

        if (recognition) {
            try { recognition.abort(); } catch (e) {}
            try { recognition.stop(); } catch (e) {}
            cleanupRecognition();
        }
        console.log('[VoiceAssistant] Recognition stopped intentionally');

        stopAllAudio();
        console.log('[VoiceAssistant] Pending audio cancelled');

        accumulatedTranscript = '';
        currentInterimText = '';
        isFinalizing = false;
        hideSendArea();

        updateUIForState(AssistantState.STOPPED);
        if (hudTranscript) {
            hudTranscript.textContent = 'Voice assistant stopped. Click Start Voice or double-click to speak.';
        }
        if (hudStateLabel) {
            hudStateLabel.textContent = 'Voice assistant stopped.';
        }
        console.log(`[VoiceAssistant] Session invalidated: ${cancelledId}`);
        console.log('[VoiceAssistant] Returned to IDLE');
    }

    // ======================================================================
    //  11. Event Handlers & Double-Click Toggle
    // ======================================================================
    document.addEventListener('dblclick', (event) => {
        const target = event.target;
        if (
            target.closest('input') ||
            target.closest('textarea') ||
            target.closest('button') ||
            target.closest('a') ||
            target.closest('#daniel-ai-chatbot') ||
            target.closest('.va-hud-send-input') ||
            target.isContentEditable
        ) {
            return;
        }

        const now = Date.now();
        if (now - lastToggleTime < 400) return;
        lastToggleTime = now;

        if (voiceSessionActive) {
            stopVoiceSession();
        } else {
            startNewVoiceSession();
        }
    });

    if (hudPill) {
        hudPill.addEventListener('click', (e) => {
            e.stopPropagation();
            const now = Date.now();
            if (now - lastToggleTime < 400) return; // Debounce rapid clicks
            lastToggleTime = now;
            if (voiceSessionActive) {
                stopVoiceSession();
            } else {
                startNewVoiceSession();
            }
        });
    }

    if (sessionBtn) {
        sessionBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const now = Date.now();
            if (now - lastToggleTime < 400) return; // Debounce rapid clicks
            lastToggleTime = now;
            if (voiceSessionActive) {
                stopVoiceSession();
            } else {
                startNewVoiceSession();
            }
        });
    }

    // Initialize in clean OFF / IDLE state on page load/refresh
    updateUIForState(AssistantState.IDLE);

})();
