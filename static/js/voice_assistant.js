/**
 * Daniel John Britto - AI Voice Assistant & Natural Conversation Controller
 *
 * COMPLETE CONVERSATIONAL VOICE PIPELINE:
 * 1. Activation: DOUBLE-CLICK ANYWHERE ON SCREEN (No mic or start buttons)
 * 2. Speech-to-Text: Browser SpeechRecognition / webkitSpeechRecognition
 * 3. 5-Second Silence Detection: Waits for complete question before showing Send
 * 4. Send Button + Try Again: Visitor MUST click Send before Gemini is called
 * 5. AI Question Analysis: Google Gemini API + PostgreSQL/Resume RAG
 * 6. Voice Generation: Natural server-side Google TTS audio with SpeechSynthesis fallback
 * 7. Automatic Spoken Answer: AI speaks answer aloud immediately after generation
 * 8. Instant Replay: Replays exact last answer without re-querying Gemini
 * 9. Voice Commands: "Repeat that", "Stop speaking", "Stop listening", "Goodbye", etc.
 * 10. Continuous Mode: Natural back-and-forth hands-free voice dialogue
 * 11. Separation: 100% independent from the text chatbot.
 */

(() => {
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
    const stopBtn         = document.getElementById('va-stop-btn');
    const continuousBtn   = document.getElementById('va-continuous-btn');
    // Send & Try Again button area elements
    const sendArea        = document.getElementById('va-hud-send-area');
    const sendInput       = document.getElementById('va-hud-send-input');
    const sendBtn         = document.getElementById('va-send-btn');
    const tryAgainBtn     = document.getElementById('va-try-again-btn');

    if (!hudContainer) return;

    // ──────────────────────────────────────────────────
    //  Explicit State Model
    // ──────────────────────────────────────────────────
    const AssistantState = {
        INACTIVE:              'inactive',
        STARTING:              'starting',
        LISTENING:             'listening',
        PROCESSING_TRANSCRIPT: 'processing_transcript',
        AWAITING_CONFIRMATION: 'awaiting_confirmation',
        SENDING:               'sending',
        SPEAKING:              'speaking',
        STOPPED:               'stopped'
    };

    let currentState          = AssistantState.INACTIVE;
    let continuousMode        = true;
    let recognition           = null;
    let currentAudio          = null;
    let synth                 = window.speechSynthesis || null;
    let availableVoices       = [];
    let selectedVoice         = null;
    let currentUtterance      = null;
    let lastSpokenAnswer      = '';
    let lastAudioUrl          = '';
    let voiceHistory          = [];

    // Session and retry management
    let isStarting            = false;
    let isIntentionalStop     = false;
    let shouldRestartOnEnd    = false;
    let currentSessionId      = 0;
    let noSpeechRetryCount    = 0;
    const MAX_NO_SPEECH_RETRIES = 2;
    let lastToggleTime        = 0;
    let pendingStartTimeout   = null;

    // 5-Second Silence Detection Variables
    const SILENCE_WAIT_MS     = 5000;
    const COUNTDOWN_INTERVAL  = 1000;
    let silenceTimer          = null;
    let countdownInterval     = null;
    let accumulatedTranscript = '';
    let currentInterimText    = '';
    let hasSpokenThisSession  = false;

    // Preferred language detection
    function getPreferredLanguage() {
        if (navigator.language && navigator.language.startsWith('en')) {
            return navigator.language;
        }
        return 'en-IN';
    }

    // ======================================================================
    //  Centralized UI State Synchronizer
    //  Guarantees 100% consistency across all UI components at all times.
    // ======================================================================
    function updateUIForState(state) {
        currentState = state;

        // Clean slate of state classes
        hudContainer.classList.remove('is-listening', 'is-speaking', 'is-ready', 'is-inactive', 'is-active');

        switch (state) {
            case AssistantState.INACTIVE:
                hudContainer.classList.add('is-inactive');
                if (hudCard) hudCard.setAttribute('hidden', '');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Double-click anywhere to speak';
                if (hudStateLabel) hudStateLabel.textContent = 'Inactive';
                if (hudSpeaker) hudSpeaker.textContent = 'Status';
                hideSendArea();
                break;

            case AssistantState.STARTING:
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
                hideSendArea();
                break;

            case AssistantState.PROCESSING_TRANSCRIPT:
                hudContainer.classList.add('is-active');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Finalizing question...';
                if (hudStateLabel) hudStateLabel.textContent = 'Processing your speech...';
                if (hudSpeaker) hudSpeaker.textContent = 'Your Question';
                break;

            case AssistantState.AWAITING_CONFIRMATION:
                hudContainer.classList.add('is-active', 'is-ready');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Question ready — Click Send';
                if (hudStateLabel) hudStateLabel.textContent = 'Review your question and click Send';
                if (hudSpeaker) hudSpeaker.textContent = 'Your Question';
                break;

            case AssistantState.SENDING:
                hudContainer.classList.add('is-active');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Thinking...';
                if (hudStateLabel) hudStateLabel.textContent = 'Thinking with Gemini AI...';
                if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI';
                if (hudTranscript) hudTranscript.textContent = 'Analyzing your question...';
                hideSendArea();
                break;

            case AssistantState.SPEAKING:
                hudContainer.classList.add('is-active', 'is-speaking');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.removeAttribute('hidden');
                if (hudStatusText) hudStatusText.textContent = 'Daniel is speaking... (Double-click to stop)';
                if (hudStateLabel) hudStateLabel.textContent = 'Daniel AI Spoken Answer';
                if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI';
                hideSendArea();
                break;

            case AssistantState.STOPPED:
                hudContainer.classList.add('is-active');
                if (hudCard) hudCard.removeAttribute('hidden');
                if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');
                if (hudStatusText) hudStatusText.textContent = 'Stopped';
                if (hudStateLabel) hudStateLabel.textContent = 'Stopped. Double-click anywhere to speak again.';
                if (hudSpeaker) hudSpeaker.textContent = 'Assistant Paused';
                if (hudTranscript && !accumulatedTranscript) {
                    hudTranscript.textContent = 'Assistant is paused. Double-click anywhere on the screen to talk again.';
                }
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
    //  2. Speech Synthesis Setup
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

    // ======================================================================
    //  3. Audio Playback Management (Dual Engine)
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

    function playGeneratedAudio(audioUrl, fallbackText) {
        stopAllAudio();
        stopListening(true); // Isolate mic from assistant voice

        updateUIForState(AssistantState.SPEAKING);
        console.log('[VoiceAssistant Diagnostic] Speech synthesis started.');

        if (audioUrl) {
            try {
                const audio = new Audio(audioUrl);
                currentAudio = audio;

                audio.onplay = () => {};
                audio.onended = () => { handleSpeechEnded(); };
                audio.onerror = (err) => {
                    console.warn('Server audio failed; using SpeechSynthesis fallback:', err);
                    currentAudio = null;
                    playSpeechSynthesisFallback(fallbackText, false);
                };

                const playPromise = audio.play();
                if (playPromise !== undefined) {
                    playPromise.catch((err) => {
                        console.warn('Autoplay error; falling back to SpeechSynthesis:', err);
                        currentAudio = null;
                        playSpeechSynthesisFallback(fallbackText, false);
                    });
                }
                return;
            } catch (e) {
                console.warn('Audio element error; falling back:', e);
            }
        }

        playSpeechSynthesisFallback(fallbackText, false);
    }

    function playSpeechSynthesisFallback(text, shouldStopAudio = true) {
        if (shouldStopAudio) {
            stopAllAudio();
            stopListening(true);
            updateUIForState(AssistantState.SPEAKING);
            console.log('[VoiceAssistant Diagnostic] Speech synthesis started.');
        }

        if (!synth) { handleSpeechEnded(); return; }

        const clean = cleanTextForSpeech(text);
        if (!clean) { handleSpeechEnded(); return; }

        currentUtterance = new SpeechSynthesisUtterance(clean);
        currentUtterance.rate = 1.0;
        currentUtterance.pitch = 1.0;
        if (selectedVoice) currentUtterance.voice = selectedVoice;

        currentUtterance.onstart = () => {};
        currentUtterance.onend = () => { handleSpeechEnded(); };
        currentUtterance.onerror = (err) => {
            console.warn('SpeechSynthesis error:', err);
            handleSpeechEnded();
        };

        try {
            synth.speak(currentUtterance);
        } catch (e) {
            console.warn('Error starting speech synthesis:', e);
            handleSpeechEnded();
        }
    }

    function handleSpeechEnded() {
        console.log('[VoiceAssistant Diagnostic] Speech synthesis completed.');
        hudContainer.classList.remove('is-speaking');
        if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');

        if (currentState === AssistantState.INACTIVE) {
            updateUIForState(AssistantState.INACTIVE);
            return;
        }

        if (continuousMode) {
            updateUIForState(AssistantState.LISTENING);
            setTimeout(() => {
                if (currentState !== AssistantState.INACTIVE && currentState !== AssistantState.SENDING) {
                    hideSendArea();
                    accumulatedTranscript = '';
                    currentInterimText = '';
                    hasSpokenThisSession = false;
                    startListening();
                }
            }, 600);
        } else {
            updateUIForState(AssistantState.STOPPED);
        }
    }

    // ======================================================================
    //  4. Send & Try Again Area Management
    // ======================================================================
    function showSendArea(questionText) {
        if (!sendArea || !sendInput || !sendBtn) return;

        updateUIForState(AssistantState.AWAITING_CONFIRMATION);

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
        if (!sendInput || currentState === AssistantState.SENDING) return;

        const question = (sendInput.textContent || sendInput.innerText || '').trim();
        if (!question) {
            if (hudTranscript) hudTranscript.textContent = 'Please speak or type a question first.';
            return;
        }

        // Disable button to prevent duplicate submissions
        if (sendBtn) sendBtn.disabled = true;

        // Stop any active recognition
        stopListening(true);

        // Hide send area
        hideSendArea();

        // Check for voice command first
        const isCommand = checkVoiceCommand(question);
        if (!isCommand) {
            processSpokenQuery(question);
        } else {
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    function handleTryAgain() {
        clearSilenceTimer();
        stopAllAudio();
        noSpeechRetryCount = 0;
        accumulatedTranscript = '';
        currentInterimText = '';
        hasSpokenThisSession = false;
        hideSendArea();
        startListening();
    }

    // Wire up the Send button
    if (sendBtn) {
        sendBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleSendClick();
        });
    }

    // Wire up the Try Again button
    if (tryAgainBtn) {
        tryAgainBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleTryAgain();
        });
    }

    // Dynamic button validation when visitor edits the question text
    if (sendInput) {
        sendInput.addEventListener('input', () => {
            const text = (sendInput.textContent || sendInput.innerText || '').trim();
            if (sendBtn) sendBtn.disabled = !text;
        });

        // Allow Enter key to send (Shift+Enter for newline)
        sendInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendClick();
            }
        });
    }

    // ======================================================================
    //  5. Instant Answer Replay Feature
    // ======================================================================
    function replayLastAnswer() {
        if (!lastSpokenAnswer && !lastAudioUrl) {
            if (hudTranscript) hudTranscript.textContent = "There is no previous answer to replay yet.";
            return;
        }

        console.log('[VoiceAssistant Diagnostic] Replaying previous answer without Gemini call.');
        stopListening(true);
        hideSendArea();
        if (hudSpeaker) hudSpeaker.textContent = 'Daniel AI (Replay)';
        if (hudTranscript) hudTranscript.textContent = lastSpokenAnswer;

        playGeneratedAudio(lastAudioUrl, lastSpokenAnswer);
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

        if (['stop speaking', 'stop talking', 'be quiet', 'pause audio'].includes(text)) {
            stopAllAudio();
            updateUIForState(AssistantState.STOPPED);
            return true;
        }

        if (['stop listening', 'pause listening', 'stop recording'].includes(text)) {
            stopListening(true);
            updateUIForState(AssistantState.STOPPED);
            return true;
        }

        if (text === 'stop') {
            stopAllAudio();
            stopListening(true);
            updateUIForState(AssistantState.STOPPED);
            return true;
        }

        if (['continue', 'resume', 'keep going'].includes(text)) {
            if (currentState !== AssistantState.INACTIVE && currentState !== AssistantState.SPEAKING) {
                hideSendArea();
                startListening();
            }
            return true;
        }

        if (['goodbye', 'bye', 'exit', 'close assistant', 'turn off'].includes(text)) {
            deactivateAssistant();
            return true;
        }

        return false;
    }

    // ======================================================================
    //  7. 5-Second Silence Detection
    //     After 5s of silence the recognized text is DISPLAYED with a Send
    //     button. Gemini is NOT called until the visitor clicks Send.
    // ======================================================================
    function clearSilenceTimer() {
        if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
        if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }
    }

    function resetSilenceTimer() {
        clearSilenceTimer();

        // Check either accumulated finalized text OR currently spoken interim text
        const activeSpeech = (accumulatedTranscript + ' ' + currentInterimText).trim();
        if (!activeSpeech) return;

        console.log('[VoiceAssistant Diagnostic] Silence timer started.');

        let remainingSeconds = Math.ceil(SILENCE_WAIT_MS / 1000);
        if (hudStateLabel) {
            hudStateLabel.textContent = `Waiting ${remainingSeconds}s for you to continue...`;
        }

        countdownInterval = setInterval(() => {
            remainingSeconds--;
            if (remainingSeconds > 0) {
                if (hudStateLabel) {
                    hudStateLabel.textContent = `Waiting ${remainingSeconds}s for you to continue...`;
                }
            } else {
                clearInterval(countdownInterval);
                countdownInterval = null;
            }
        }, COUNTDOWN_INTERVAL);

        silenceTimer = setTimeout(() => {
            clearSilenceTimer();
            console.log('[VoiceAssistant Diagnostic] Silence timer completed.');
            finalizeAccumulatedSpeech();
        }, SILENCE_WAIT_MS);
    }

    /**
     * Called after exactly 5 seconds of silence.
     * Captures complete transcript including any pending interim words.
     * DOES NOT call Gemini — only shows the recognized text + Send button.
     */
    function finalizeAccumulatedSpeech() {
        updateUIForState(AssistantState.PROCESSING_TRANSCRIPT);

        // Include both accumulated final text and any pending interim words so no speech is lost
        const completeQuery = (accumulatedTranscript + (currentInterimText ? ' ' + currentInterimText : '')).trim();
        currentInterimText = '';

        if (!completeQuery) {
            if (currentState === AssistantState.PROCESSING_TRANSCRIPT) {
                updateUIForState(AssistantState.LISTENING);
            }
            return;
        }

        accumulatedTranscript = completeQuery;
        hasSpokenThisSession = false;

        // Intentionally stop listening while the visitor reviews the question
        stopListening(true);

        // Show the Send button area with the recognized question
        showSendArea(completeQuery);
    }

    // ======================================================================
    //  8. Robust Speech Recognition Lifecycle (Web Speech API)
    // ======================================================================
    function cleanupRecognition() {
        if (!recognition) return;
        const oldRec = recognition;
        recognition = null;
        try {
            oldRec.onstart = null;
            oldRec.onaudiostart = null;
            oldRec.onspeechstart = null;
            oldRec.onresult = null;
            oldRec.onerror = null;
            oldRec.onend = null;
            oldRec.stop();
        } catch (e) {
            try { oldRec.abort(); } catch (err) {}
        }
    }

    function createFreshRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return null;

        const thisSessionId = ++currentSessionId;
        const rec = new SpeechRecognition();
        rec.continuous     = true;
        rec.interimResults = true;
        rec.lang           = getPreferredLanguage();

        rec.onstart = () => {
            if (thisSessionId !== currentSessionId) return;
            updateUIForState(AssistantState.LISTENING);
            isIntentionalStop = false;
            // NOTE: Do NOT reset noSpeechRetryCount here.
            // Resetting here defeats the bounded retry limit.
        };

        rec.onresult = (event) => {
            if (thisSessionId !== currentSessionId) return;
            console.log('[VoiceAssistant Diagnostic] Recognition result received.');
            noSpeechRetryCount = 0; // Actual speech received; reset retry counter

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
                console.log('[VoiceAssistant Diagnostic] Interim transcript:', currentInterimText);
            } else {
                currentInterimText = '';
            }

            if (sessionFinal.trim()) {
                accumulatedTranscript = sessionFinal.trim();
                hasSpokenThisSession = true;
                console.log('[VoiceAssistant Diagnostic] Final transcript:', accumulatedTranscript);
            }

            const liveCombined = (accumulatedTranscript + (currentInterimText ? ' ' + currentInterimText : '')).trim();

            if (liveCombined) {
                hasSpokenThisSession = true;
                if (hudTranscript) {
                    hudTranscript.textContent = `"${liveCombined}..."`;
                }

                // Reset 5-second silence timer on every speech event
                resetSilenceTimer();
            }
        };

        rec.onerror = (event) => {
            if (thisSessionId !== currentSessionId) return;
            console.log('[VoiceAssistant Diagnostic] Recognition error:', event.error);

            if (event.error === 'aborted') {
                if (isIntentionalStop) {
                    return;
                }
                console.log('[VoiceAssistant Diagnostic] Unexpected abort.');
                return;
            }

            if (event.error === 'no-speech') {
                // If user already spoke words and paused, finalize that question
                const hasSpeech = (accumulatedTranscript || currentInterimText).trim();
                if (hasSpeech) {
                    clearSilenceTimer();
                    finalizeAccumulatedSpeech();
                    return;
                }

                // No speech was detected: Bounded recovery strategy
                noSpeechRetryCount++;
                if (noSpeechRetryCount <= MAX_NO_SPEECH_RETRIES && !isIntentionalStop && currentState === AssistantState.LISTENING) {
                    shouldRestartOnEnd = true;
                    console.log(`[VoiceAssistant Diagnostic] No speech detected (attempt ${noSpeechRetryCount}/${MAX_NO_SPEECH_RETRIES}). Re-listening...`);
                    if (hudStateLabel) hudStateLabel.textContent = `Still listening... (attempt ${noSpeechRetryCount + 1}/${MAX_NO_SPEECH_RETRIES + 1})`;
                } else {
                    shouldRestartOnEnd = false;
                    console.log(`[VoiceAssistant Diagnostic] No speech retry limit reached (${noSpeechRetryCount}/${MAX_NO_SPEECH_RETRIES}). Stopping.`);
                    stopListening(false);
                    updateUIForState(AssistantState.STOPPED);
                    if (hudTranscript) {
                        hudTranscript.textContent = 'No speech was detected. Double-click anywhere when you are ready to speak.';
                    }
                    if (hudStateLabel) {
                        hudStateLabel.textContent = 'Stopped (silence timeout)';
                    }
                }
                return;
            }

            if (event.error === 'not-allowed') {
                shouldRestartOnEnd = false;
                clearSilenceTimer();
                accumulatedTranscript = '';
                currentInterimText = '';
                stopListening(false);
                updateUIForState(AssistantState.STOPPED);
                if (hudTranscript) hudTranscript.textContent = 'Microphone permission was denied. Please allow microphone access in your browser settings.';
                if (hudStateLabel) hudStateLabel.textContent = 'Microphone permission required';
                return;
            }

            if (event.error === 'audio-capture') {
                shouldRestartOnEnd = false;
                clearSilenceTimer();
                stopListening(false);
                updateUIForState(AssistantState.STOPPED);
                if (hudTranscript) hudTranscript.textContent = 'No microphone was detected or microphone is in use by another application.';
                if (hudStateLabel) hudStateLabel.textContent = 'Audio capture error';
                return;
            }

            if (event.error === 'network') {
                shouldRestartOnEnd = false;
                clearSilenceTimer();
                stopListening(false);
                updateUIForState(AssistantState.STOPPED);
                if (hudTranscript) hudTranscript.textContent = 'Network error connecting to speech recognition service. Please check your internet connection.';
                if (hudStateLabel) hudStateLabel.textContent = 'Network error';
                return;
            }

            // Fallback for any other unexpected error
            shouldRestartOnEnd = false;
            const hasSpeech = (accumulatedTranscript || currentInterimText).trim();
            if (hasSpeech) {
                clearSilenceTimer();
                finalizeAccumulatedSpeech();
            } else {
                clearSilenceTimer();
                stopListening(false);
                updateUIForState(AssistantState.STOPPED);
                if (hudTranscript) hudTranscript.textContent = 'Could not catch that clearly. Please speak again or double-click to stop.';
            }
        };

        rec.onend = () => {
            if (thisSessionId !== currentSessionId) return;
            console.log('[VoiceAssistant Diagnostic] Recognition ended.');

            // Check if bounded retry is active
            if (shouldRestartOnEnd && !isIntentionalStop && (currentState === AssistantState.LISTENING || currentState === AssistantState.STARTING)) {
                shouldRestartOnEnd = false;
                console.log('[VoiceAssistant Diagnostic] Bounded recovery restarting recognition...');
                cleanupRecognition();
                if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
                pendingStartTimeout = setTimeout(() => {
                    if (!isIntentionalStop && (currentState === AssistantState.LISTENING || currentState === AssistantState.STARTING)) {
                        startListening();
                    }
                }, 200);
                return;
            }

            shouldRestartOnEnd = false;

            // If recognition ended and was not intentionally stopped, or if state is still
            // STARTING/LISTENING, update UI to STOPPED so UI never shows listening when mic is dead.
            if (currentState === AssistantState.LISTENING || currentState === AssistantState.STARTING) {
                updateUIForState(AssistantState.STOPPED);
            }
        };

        return rec;
    }

    async function startListening() {
        if (isStarting || currentState === AssistantState.SENDING || currentState === AssistantState.SPEAKING) return;
        isStarting = true;

        try {
            clearSilenceTimer();
            if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }

            currentInterimText = '';
            isIntentionalStop = false;
            updateUIForState(AssistantState.STARTING);

            // Non-destructive permission check: do NOT open/stop getUserMedia audio tracks,
            // as track.stop() puts the Windows audio capture device into teardown and mutes SpeechRecognition.
            if (navigator.permissions && navigator.permissions.query) {
                try {
                    const status = await navigator.permissions.query({ name: 'microphone' });
                    if (status.state === 'denied') {
                        updateUIForState(AssistantState.STOPPED);
                        if (hudTranscript) hudTranscript.textContent = 'Microphone permission was denied. Please allow microphone access in your browser settings.';
                        if (hudStateLabel) hudStateLabel.textContent = 'Microphone permission required';
                        return;
                    }
                } catch (permErr) {
                    // Some browsers don't support querying 'microphone'; let SpeechRecognition handle natively
                }
            }

            // Ensure state was not cancelled during pre-flight await
            if (currentState === AssistantState.INACTIVE || currentState === AssistantState.STOPPED || isIntentionalStop) {
                return;
            }

            // Clean up any lingering previous instance before creating a fresh one
            cleanupRecognition();

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                updateUIForState(AssistantState.STOPPED);
                alert('Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Apple Safari.');
                return;
            }

            recognition = createFreshRecognition();
            if (!recognition) {
                updateUIForState(AssistantState.STOPPED);
                return;
            }

            console.log('[VoiceAssistant Diagnostic] Recognition started.');
            recognition.start();
        } catch (e) {
            console.warn('Recognition start caught exception:', e);
            updateUIForState(AssistantState.STOPPED);
            cleanupRecognition();
        } finally {
            isStarting = false;
        }
    }

    function stopListening(isIntentional = true) {
        clearSilenceTimer();
        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }
        shouldRestartOnEnd = false;

        isIntentionalStop = isIntentional;
        if (isIntentional) {
            console.log('[VoiceAssistant Diagnostic] Intentional stop.');
        }

        hudContainer.classList.remove('is-listening');
        if (hudMiniWave) hudMiniWave.setAttribute('hidden', '');

        if (recognition) {
            try {
                recognition.stop();
            } catch (e) {
                try { recognition.abort(); } catch (err) {}
            }
        }
    }

    // ======================================================================
    //  9. AI Question Analysis & Answer Generation (Gemini RAG)
    //     ONLY called when the visitor clicks the Send button.
    // ======================================================================
    async function processSpokenQuery(question) {
        if (!question || currentState === AssistantState.SENDING) return;

        updateUIForState(AssistantState.SENDING);
        stopAllAudio();
        stopListening(true);
        hideSendArea();

        console.log('[VoiceAssistant Diagnostic] Gemini request started.');

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
                })
            });

            console.log('[VoiceAssistant Diagnostic] Gemini response received.');

            if (response.ok) {
                const data = await response.json();
                const botAnswer = data.answer || "I don't have verified information about that in Daniel's portfolio. You can contact Daniel directly at danieljohnbrittoaj@gmail.com.";
                const audioUrl = data.audio_url || '';

                lastSpokenAnswer = botAnswer;
                lastAudioUrl = audioUrl;
                voiceHistory.push({ role: 'user', text: question });
                voiceHistory.push({ role: 'model', text: botAnswer });

                if (hudTranscript) hudTranscript.textContent = botAnswer;
                if (replayBtn) replayBtn.style.display = 'inline-flex';

                // Automatically speak the answer aloud
                playGeneratedAudio(audioUrl, botAnswer);
            } else if (response.status === 429) {
                const rateMsg = "You are asking questions very quickly. Please wait a moment before asking again.";
                if (hudTranscript) hudTranscript.textContent = rateMsg;
                playGeneratedAudio('', rateMsg);
            } else {
                const errMsg = "I encountered a temporary connection issue. You can reach Daniel directly at danieljohnbrittoaj@gmail.com.";
                if (hudTranscript) hudTranscript.textContent = errMsg;
                playGeneratedAudio('', errMsg);
            }
        } catch (err) {
            console.error('Voice assistant error:', err);
            const netMsg = "Network error connecting to Daniel's voice assistant. Please check your connection.";
            if (hudTranscript) hudTranscript.textContent = netMsg;
            playGeneratedAudio('', netMsg);
        } finally {
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    // ======================================================================
    //  10. Activation & Deactivation
    // ======================================================================
    function activateAssistant() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Apple Safari.');
            return;
        }

        noSpeechRetryCount = 0;
        accumulatedTranscript = '';
        currentInterimText = '';
        hasSpokenThisSession = false;

        hideSendArea();
        startListening();
    }

    function deactivateAssistant() {
        updateUIForState(AssistantState.INACTIVE);
        clearSilenceTimer();
        if (pendingStartTimeout) { clearTimeout(pendingStartTimeout); pendingStartTimeout = null; }

        stopAllAudio();
        stopListening(true);
        cleanupRecognition();
        hideSendArea();

        accumulatedTranscript = '';
        currentInterimText = '';
        hasSpokenThisSession = false;
    }

    function toggleAssistant() {
        if (currentState === AssistantState.STOPPED) {
            activateAssistant();
        } else if (currentState !== AssistantState.INACTIVE) {
            deactivateAssistant();
        } else {
            activateAssistant();
        }
    }

    // ======================================================================
    //  11. Event Handlers & Double-Click Listener
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

        // Prevent rapid double-click bouncing
        const now = Date.now();
        if (now - lastToggleTime < 400) return;
        lastToggleTime = now;

        toggleAssistant();
    });

    if (hudPill) {
        hudPill.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleAssistant();
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            stopAllAudio();
            stopListening(true);
            updateUIForState(AssistantState.STOPPED);
        });
    }

    if (continuousBtn) {
        continuousBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            continuousMode = !continuousMode;
            continuousBtn.classList.toggle('is-active', continuousMode);
            continuousBtn.setAttribute('aria-pressed', continuousMode ? 'true' : 'false');
        });
    }

})();
