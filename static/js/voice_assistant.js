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
    let currentAttemptId      = 0;
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

    // No-speech retry management
    const MAX_NO_SPEECH_RETRIES = 3;
    let noSpeechRetryCount      = 0;

    // Safety timeout: restart recognition if audio flows but no results arrive (increased to 12s)
    const RECOGNITION_SAFETY_TIMEOUT_MS = 12000;
    let recognitionSafetyTimer = null;
    let hasLoggedMicDiagnostics = false;

    // ──────────────────────────────────────────────────
    //  Speech Recognition Capability Check & Mobile Diagnostics
    // ──────────────────────────────────────────────────
    const SpeechRecognitionCapability = window.SpeechRecognition || window.webkitSpeechRecognition;
    const isSpeechSupported = !!SpeechRecognitionCapability;
    const isSecureContext = window.isSecureContext || window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    console.log(`[VoiceAssistant] SpeechRecognition supported: ${isSpeechSupported}`);
    console.log(`[VoiceAssistant] User agent: ${navigator.userAgent}`);
    console.log(`[VoiceAssistant] Platform: ${navigator.platform || navigator.userAgentData?.platform || 'Unknown'}`);
    console.log(`[VoiceAssistant][MobileDebug] userAgent: ${navigator.userAgent}`);
    console.log(`[VoiceAssistant][MobileDebug] SpeechRecognition supported: ${isSpeechSupported}`);
    if (!isSecureContext) {
        console.warn('[VoiceAssistant][MobileDebug] WARNING: Not running in secure HTTPS context. Microphones will fail on mobile browsers.');
    }

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
                if (hudStatusText) hudStatusText.textContent = 'Tap to speak or double-tap anywhere';
                if (hudStateLabel) hudStateLabel.textContent = 'Voice Assistant (Idle)';
                if (hudSpeaker) hudSpeaker.textContent = 'Status';
                if (hudTranscript) hudTranscript.textContent = 'Tap Start Voice or double-tap anywhere on screen to talk to Daniel.';
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

        let speechEnded = false;
        const wordCount = (clean.split(/\s+/).length) || 10;
        const watchdogMs = Math.max(4000, Math.min(25000, (wordCount / 2.2) * 1000 + 3500));

        const watchdog = setTimeout(() => {
            if (!speechEnded && thisSessionId === currentSessionId && voiceSessionActive) {
                console.log('[VoiceAssistant] Speech synthesis watchdog triggered (mobile safeguard)');
                speechEnded = true;
                handleSpeechEnded(thisSessionId);
            }
        }, watchdogMs);

        utterance.onend = () => {
            if (speechEnded) return;
            speechEnded = true;
            clearTimeout(watchdog);
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }
            handleSpeechEnded(thisSessionId);
        };

        utterance.onerror = (err) => {
            if (speechEnded) return;
            speechEnded = true;
            clearTimeout(watchdog);
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
            clearTimeout(watchdog);
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

    function clearSafetyTimer() {
        if (recognitionSafetyTimer) {
            clearTimeout(recognitionSafetyTimer);
            recognitionSafetyTimer = null;
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
    //  8. Speech Recognition Lifecycle & Attempt Architecture
    // ======================================================================

    /**
     * Non-intrusive diagnostic probe: inspects microphone permission safely.
     * Does NOT acquire or tear down hardware media tracks, protecting SpeechRecognition on mobile.
     */
    function logMicrophoneDiagnostics() {
        if (hasLoggedMicDiagnostics) return;
        hasLoggedMicDiagnostics = true;

        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: 'microphone' })
                .then((status) => {
                    console.log(`[VoiceAssistant] Microphone permission status: ${status.state}`);
                    console.log(`[VoiceAssistant][MobileDebug] microphone permission: ${status.state}`);
                })
                .catch((e) => {
                    console.log(`[VoiceAssistant][MobileDebug] permissions.query for microphone not available: ${e.message}`);
                });
        } else {
            console.log('[VoiceAssistant][MobileDebug] permissions.query not supported in this browser');
        }
    }

    /**
     * Safe asynchronous restart scheduler: ensures the previous recognition instance
     * has settled before starting the next attempt.
     * Note: currentAttemptId is strictly incremented by startListening() only.
     */
    function scheduleRestart(thisSessionId, delayMs = 300) {
        if (thisSessionId !== currentSessionId || !voiceSessionActive || intentionalStop) {
            return;
        }

        if (pendingStartTimeout) {
            clearTimeout(pendingStartTimeout);
            pendingStartTimeout = null;
        }

        pendingStartTimeout = setTimeout(() => {
            pendingStartTimeout = null;
            if (thisSessionId === currentSessionId && voiceSessionActive && !intentionalStop && currentState === AssistantState.LISTENING) {
                startListening(thisSessionId);
            }
        }, delayMs);
    }

    /**
     * Centralized retry handler: SINGLE OWNER of noSpeechRetryCount increments.
     * Handles both safety timeouts and native no-speech errors consistently.
     */
    function handleNoSpeechRetry(thisSessionId, thisAttemptId, triggerSource) {
        if (thisSessionId !== currentSessionId || thisAttemptId !== currentAttemptId || !voiceSessionActive || intentionalStop) {
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Ignoring stale retry trigger (${triggerSource})`);
            return;
        }

        noSpeechRetryCount++;
        console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] No speech detected (${triggerSource}, attempt ${noSpeechRetryCount}/${MAX_NO_SPEECH_RETRIES})`);

        if (noSpeechRetryCount < MAX_NO_SPEECH_RETRIES && !hasSpokenThisSession) {
            recognitionErrorHandled = true;
            shouldRestartOnEnd = true;
            if (hudTranscript) {
                hudTranscript.textContent = 'Still listening... Speak now.';
            }
            scheduleRestart(thisSessionId, 300);
            return;
        }

        // Maximum retries reached: terminate cleanly without exceeding limit
        console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Max no-speech retries reached (${noSpeechRetryCount}/${MAX_NO_SPEECH_RETRIES}), stopping session`);
        recognitionErrorHandled = true;
        shouldRestartOnEnd = false;
        stopVoiceSession();
        if (hudSpeaker) hudSpeaker.textContent = 'You (Speaking)';
        if (hudTranscript) {
            hudTranscript.textContent = 'No speech was detected. Click Start Voice or double-click to speak.';
        }
        showSendArea('');
    }

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

    function createFreshRecognition(thisSessionId, thisAttemptId) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return null;

        const rec = new SpeechRecognition();
        rec.continuous     = false;
        rec.interimResults = true;
        rec.lang           = getPreferredLanguage();
        rec.maxAlternatives = 3;

        let sessionHadSpeech = false;

        function isCurrentAttemptValid() {
            return thisSessionId === currentSessionId &&
                   thisAttemptId === currentAttemptId &&
                   voiceSessionActive &&
                   !intentionalStop;
        }

        rec.onstart = () => {
            console.log(`[VoiceAssistant][MobileDebug] onstart (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Ignoring stale onstart`);
                try { rec.abort(); } catch (e) {}
                return;
            }
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Recognition started (lang: ${rec.lang}, continuous: false)`);
            updateUIForState(AssistantState.LISTENING);

            // Safety watchdog: if no results arrive within 12s, trigger centralized retry
            clearSafetyTimer();
            recognitionSafetyTimer = setTimeout(() => {
                if (!isCurrentAttemptValid()) return;
                if (!hasSpokenThisSession && currentState === AssistantState.LISTENING) {
                    console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Safety timeout (${RECOGNITION_SAFETY_TIMEOUT_MS}ms): no results received`);
                    handleNoSpeechRetry(thisSessionId, thisAttemptId, 'safety-timeout');
                }
            }, RECOGNITION_SAFETY_TIMEOUT_MS);
        };

        // ── Diagnostic handlers: trace browser audio pipeline with session & attempt ID ──
        rec.onaudiostart = () => {
            console.log(`[VoiceAssistant][MobileDebug] onaudiostart (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Audio capture started`);
        };
        rec.onaudioend = () => {
            console.log(`[VoiceAssistant][MobileDebug] onaudioend (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Audio capture ended`);
        };
        rec.onsoundstart = () => {
            console.log(`[VoiceAssistant][MobileDebug] onsoundstart (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Sound detected`);
        };
        rec.onsoundend = () => {
            console.log(`[VoiceAssistant][MobileDebug] onsoundend (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Sound ended`);
        };
        rec.onspeechstart = () => {
            sessionHadSpeech = true;
            console.log(`[VoiceAssistant][MobileDebug] onspeechstart (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Speech detected by browser`);
        };
        rec.onspeechend = () => {
            console.log(`[VoiceAssistant][MobileDebug] onspeechend (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) return;
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Speech ended`);
        };

        rec.onresult = (event) => {
            console.log("[VoiceAssistant] RESULT EVENT RECEIVED", event);
            console.log(
                `[VoiceAssistant][MobileDebug] onresult (session: ${thisSessionId}, attempt: ${thisAttemptId}) resultIndex: ${event.resultIndex}, length: ${event.results.length}`
            );
            console.log(
                "[VoiceAssistant] resultIndex:",
                event.resultIndex,
                "results length:",
                event.results.length
            );

            for (let i = event.resultIndex; i < event.results.length; i++) {
                console.log(
                    "[VoiceAssistant] result:",
                    event.results[i][0]?.transcript,
                    "final:",
                    event.results[i].isFinal
                );
            }

            if (!isCurrentAttemptValid()) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Ignoring stale onresult`);
                return;
            }

            let sessionFinal = '';
            let sessionInterim = '';

            for (let i = 0; i < event.results.length; i++) {
                const res = event.results[i];
                const text = res[0]?.transcript?.trim();
                if (!text) continue;
                if (res.isFinal) {
                    sessionFinal += (sessionFinal ? ' ' : '') + text;
                } else {
                    sessionInterim += (sessionInterim ? ' ' : '') + text;
                }
            }

            if (sessionInterim) {
                currentInterimText = sessionInterim;
            } else {
                currentInterimText = '';
            }

            if (sessionFinal) {
                accumulatedTranscript = sessionFinal;
            }

            const liveCombined = (accumulatedTranscript + (currentInterimText ? ' ' + currentInterimText : '')).trim();

            if (liveCombined) {
                if (!hasSpokenThisSession) {
                    hasSpokenThisSession = true;
                    noSpeechRetryCount = 0;
                    clearSafetyTimer();
                    console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Speech detected: "${liveCombined}"`);
                }
                if (hudTranscript) {
                    hudTranscript.textContent = `"${liveCombined}..."`;
                }

                resetSilenceTimer(thisSessionId);
            }
        };

        rec.onerror = (event) => {
            console.log(`[VoiceAssistant][MobileDebug] onerror: ${event.error} (session: ${thisSessionId}, attempt: ${thisAttemptId})`);
            if (!isCurrentAttemptValid()) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Ignoring stale onerror (${event.error})`);
                return;
            }

            console.warn(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Recognition error: ${event.error}`);

            if (event.error === 'no-speech') {
                handleNoSpeechRetry(thisSessionId, thisAttemptId, 'onerror(no-speech)');
                return;
            }

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                recognitionErrorHandled = true;
                stopVoiceSession();
                if (hudTranscript) {
                    hudTranscript.textContent = 'Microphone permission was denied. Please allow microphone access in your browser settings.';
                }
                if (hudStateLabel) {
                    hudStateLabel.textContent = 'Microphone access denied';
                }
                showSendArea('');
                return;
            }

            if (event.error === 'audio-capture') {
                recognitionErrorHandled = true;
                stopVoiceSession();
                if (hudTranscript) {
                    hudTranscript.textContent = 'Microphone is unavailable or in use by another app. Please check your audio input device.';
                }
                if (hudStateLabel) {
                    hudStateLabel.textContent = 'Microphone unavailable';
                }
                showSendArea('');
                return;
            }

            if (event.error === 'network') {
                console.warn('[VoiceAssistant] Speech recognition network error on mobile.');
                handleNoSpeechRetry(thisSessionId, thisAttemptId, 'onerror(network)');
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
            console.log(`[VoiceAssistant][MobileDebug] onend (session: ${thisSessionId}, attempt: ${thisAttemptId}, hasSpoken: ${hasSpokenThisSession})`);
            clearSafetyTimer();

            if (!isCurrentAttemptValid()) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Ignoring stale onend`);
                recognitionErrorHandled = false;
                return;
            }
            console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Recognition ended (hasSpoken: ${hasSpokenThisSession})`);

            // If onerror already handled this cycle, only honour its decision
            if (recognitionErrorHandled) {
                recognitionErrorHandled = false;
                if (shouldRestartOnEnd && voiceSessionActive && !intentionalStop) {
                    shouldRestartOnEnd = false;
                    scheduleRestart(thisSessionId, 300);
                }
                return;
            }

            // Case A: User has spoken and we have accumulated transcript
            if (hasSpokenThisSession && accumulatedTranscript.trim()) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Phrase finalized with transcript: "${accumulatedTranscript}"`);
                if (silenceTimer && !isFinalizing) {
                    clearSilenceTimer();
                    silenceTimer = setTimeout(() => {
                        if (thisSessionId === currentSessionId && voiceSessionActive) {
                            finalizeAccumulatedSpeech(thisSessionId);
                        }
                    }, 500);
                }
                return;
            }

            // Case B: User has NOT spoken or no words recognized
            if (voiceSessionActive && !intentionalStop && !isFinalizing && currentState === AssistantState.LISTENING) {
                console.log(`[VoiceAssistant][Session:${thisSessionId}][Attempt:${thisAttemptId}][State:${currentState}] Recognition ended without speech detected`);
                handleNoSpeechRetry(thisSessionId, thisAttemptId, sessionHadSpeech ? 'onend(no-words)' : 'onend(silence)');
                return;
            }
        };

        return rec;
    }

    function startListening(sessionId) {
        if (!sessionId) sessionId = currentSessionId;
        if (sessionId !== currentSessionId || !voiceSessionActive || intentionalStop) {
            console.log(`[VoiceAssistant] Ignoring stale startListening call for session: ${sessionId}`);
            return;
        }

        const attemptId = ++currentAttemptId;
        console.log(`[VoiceAssistant][Session:${sessionId}][Attempt:${attemptId}][State:${currentState}] Recognition starting`);

        try {
            cleanupRecognition();

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                stopVoiceSession();
                console.warn('[VoiceAssistant] SpeechRecognition not supported.');
                if (hudTranscript) {
                    hudTranscript.textContent = 'Voice input is not supported in this browser. Please use Chrome on Android or Safari on iPhone.';
                }
                if (hudStatusText) {
                    hudStatusText.textContent = 'Voice input not supported';
                }
                if (hudStateLabel) {
                    hudStateLabel.textContent = 'Voice input not supported';
                }
                showSendArea('');
                updateSessionButton(false);
                return;
            }

            recognition = createFreshRecognition(sessionId, attemptId);
            if (!recognition) return;

            console.log(`[VoiceAssistant][MobileDebug] recognition.start() (session: ${sessionId}, attempt: ${attemptId})`);
            recognition.start();
        } catch (e) {
            console.warn(`[VoiceAssistant][Session:${sessionId}][Attempt:${attemptId}][State:${currentState}] Recognition start exception:`, e);
            if (sessionId === currentSessionId && voiceSessionActive) {
                stopVoiceSession();
            }
        }
    }

    function stopListening(isIntentional = true) {
        clearSilenceTimer();
        clearSafetyTimer();
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
                console.warn(`[VoiceAssistant] Backend returned status ${response.status}. Activating client-side smart fallback.`);
                const clientFallback = getClientSideFallbackAnswer(question);
                lastSpokenAnswer = clientFallback;
                lastAudioUrl = '';
                voiceHistory.push({ role: 'user', text: question });
                voiceHistory.push({ role: 'model', text: clientFallback });
                if (hudTranscript) hudTranscript.innerHTML = formatMarkdown(clientFallback);
                if (replayBtn) replayBtn.style.display = 'inline-flex';
                playGeneratedAudio('', clientFallback, thisSessionId);
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                return;
            }
            if (thisSessionId !== currentSessionId || !voiceSessionActive) {
                console.log(`[VoiceAssistant] Ignoring stale session callback: ${thisSessionId}`);
                return;
            }
            console.warn('[VoiceAssistant] Fetch error or network issue. Activating client-side smart fallback:', err.message || err);
            const clientFallback = getClientSideFallbackAnswer(question);
            lastSpokenAnswer = clientFallback;
            lastAudioUrl = '';
            voiceHistory.push({ role: 'user', text: question });
            voiceHistory.push({ role: 'model', text: clientFallback });
            if (hudTranscript) hudTranscript.innerHTML = formatMarkdown(clientFallback);
            if (replayBtn) replayBtn.style.display = 'inline-flex';
            playGeneratedAudio('', clientFallback, thisSessionId);
        } finally {
            activeFetchController = null;
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    function getClientSideFallbackAnswer(question) {
        const q = (question || '').toLowerCase().trim();
        if (q.includes('exp') || q.includes('work') || q.includes('job') || q.includes('company') || q.includes('levantare') || q.includes('role') || q.includes('career') || q.includes('current')) {
            return "Daniel John Britto A.J. is currently working as a Software Developer at Levantare Technology (Jan 2026 – Present), developing and maintaining backend services using Flask, building RESTful APIs, and managing PostgreSQL databases. Previously, he completed full-stack Python training at Besant Technologies.";
        }
        if (q.includes('skill') || q.includes('python') || q.includes('tech') || q.includes('stack') || q.includes('database') || q.includes('sql') || q.includes('language') || q.includes('framework')) {
            return "Daniel's technical skills include Python (OOP & scripting), Flask, Django, RESTful APIs, PostgreSQL, MySQL, HTML5, CSS3, JavaScript, Angular UI debugging, Git, and GitHub.";
        }
        if (q.includes('edu') || q.includes('college') || q.includes('degree') || q.includes('bachelor') || q.includes('study') || q.includes('school') || q.includes('grade') || q.includes('cgpa')) {
            return "Daniel completed his Bachelor of Engineering (B.E.) in Computer Science and Engineering from Madha Institute of Engineering and Technology, Chennai (2021–2025) with a 76.6% score. He completed Higher Secondary (81%) and Secondary School (77.4%).";
        }
        if (q.includes('project') || q.includes('ats') || q.includes('scanner') || q.includes('phishing') || q.includes('fake news') || q.includes('portfolio')) {
            return "Daniel has built several software projects: a Resume ATS Scanner, an NLP Fake News Detection System, an ML-based Phishing URL Detection model, and this full-stack Django Developer Portfolio.";
        }
        if (q.includes('contact') || q.includes('email') || q.includes('phone') || q.includes('hire') || q.includes('reach') || q.includes('call') || q.includes('mobile') || q.includes('address')) {
            return "You can reach Daniel directly via email at danieljohnbrittoaj@gmail.com or by phone at +91 9345655206. His location is Kumbakonam, Tamil Nadu.";
        }
        return "Hello! I am Daniel John Britto's AI Assistant. Daniel is a Software Developer at Levantare Technology specializing in Python, Flask, Django, PostgreSQL, and REST APIs. Feel free to ask about his experience, skills, or projects, or email him at danieljohnbrittoaj@gmail.com.";
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
        currentAttemptId = 0;
        const sessionId = currentSessionId;
        voiceSessionActive = true;
        intentionalStop = false;
        shouldRestartOnEnd = false;
        recognitionErrorHandled = false;
        accumulatedTranscript = '';
        currentInterimText = '';
        hasSpokenThisSession = false;
        isFinalizing = false;
        noSpeechRetryCount = 0;

        console.log(`[VoiceAssistant][Session:${sessionId}][Attempt:0][State:${currentState}] New session initiated`);

        stopAllAudio();
        clearSilenceTimer();
        clearSafetyTimer();
        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
        if (activeFetchController) { activeFetchController.abort(); activeFetchController = null; }

        cleanupRecognition();
        hideSendArea();

        // Prime speech synthesis on user gesture (essential for iOS Safari and Android Chrome audio unlock)
        if (synth) {
            try {
                synth.cancel();
                synth.resume();
                const primer = new SpeechSynthesisUtterance(' ');
                primer.volume = 0;
                synth.speak(primer);
            } catch (e) {}
        }

        // Run non-intrusive diagnostic check for microphone hardware once
        logMicrophoneDiagnostics();

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

        // Explicit session and attempt invalidation:
        // Any pending async callback from old session or attempt sees mismatch immediately.
        currentSessionId++;
        currentAttemptId++;
        needsSessionIncrement = false; // start will reuse the value stop just set

        console.log(`[VoiceAssistant] Cancelling session: ${cancelledId}`);

        clearSilenceTimer();
        clearSafetyTimer();
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
    //  11. Event Handlers & Double-Click / Double-Tap Toggle
    // ======================================================================
    function isInteractiveElement(target) {
        if (!target) return true;
        return !!(
            target.closest('input') ||
            target.closest('textarea') ||
            target.closest('button') ||
            target.closest('a') ||
            target.closest('#daniel-ai-chatbot') ||
            target.closest('.va-hud-send-input') ||
            target.closest('.va-hud-card') ||
            target.closest('.va-hud-pill') ||
            target.closest('#va-hud-pill') ||
            target.closest('#va-session-btn') ||
            target.isContentEditable
        );
    }

    function toggleVoiceAssistant() {
        const now = Date.now();
        if (now - lastToggleTime < 400) return; // Debounce rapid clicks/taps
        lastToggleTime = now;

        if (voiceSessionActive) {
            stopVoiceSession();
        } else {
            startNewVoiceSession();
        }
    }

    // Desktop: Standard dblclick event on non-interactive background
    document.addEventListener('dblclick', (event) => {
        if (isInteractiveElement(event.target)) return;
        toggleVoiceAssistant();
    });

    // Mobile / Touch devices: Double-tap detection via touchend on document background
    let lastTouchEndTime = 0;
    let lastTouchX = 0;
    let lastTouchY = 0;

    document.addEventListener('touchend', (event) => {
        if (!event.changedTouches || event.changedTouches.length === 0) return;
        if (isInteractiveElement(event.target)) return;

        const touch = event.changedTouches[0];
        const now = Date.now();
        const timeDiff = now - lastTouchEndTime;
        const dx = Math.abs(touch.clientX - lastTouchX);
        const dy = Math.abs(touch.clientY - lastTouchY);

        // Detect intentional double-tap within 380ms and 45px radius
        if (timeDiff > 0 && timeDiff < 380 && dx < 45 && dy < 45) {
            lastTouchEndTime = 0; // Reset to prevent triple-tap firing
            toggleVoiceAssistant();
        } else {
            lastTouchEndTime = now;
            lastTouchX = touch.clientX;
            lastTouchY = touch.clientY;
        }
    }, { passive: true });

    // Floating Pill: Single click toggle (handles both mouse and mobile tap cleanly)
    if (hudPill) {
        hudPill.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleVoiceAssistant();
        });
    }

    // Session Button inside card: Single click toggle
    if (sessionBtn) {
        sessionBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleVoiceAssistant();
        });
    }

    // Initialize in clean OFF / IDLE state on page load/refresh
    updateUIForState(AssistantState.IDLE);

})();
