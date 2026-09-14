document.addEventListener("DOMContentLoaded", () => {
    // 1. SELECT HTML UI ELEMENTS
    const orbWrapper = document.getElementById('orbWrapper');
    const statusText = document.getElementById('statusText');
    const talkBtn = document.getElementById('talkBtn');
    const userSpeech = document.getElementById('userSpeech');
    const aiReply = document.getElementById('aiReply');

    let currentAudio = null;

    // 2. TERMINATE ALL ACTIVE AUDIO PLAYBACK & SYNTHESIS
    function stopAllAudio() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            currentAudio = null;
        }
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }

    // 3. INITIALIZE WEB SPEECH RECOGNITION (MICROPHONE INPUT)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            if (orbWrapper) orbWrapper.className = 'orb-wrapper listening';
            if (statusText) statusText.innerText = "Listening... Speak now";
            if (talkBtn) talkBtn.innerText = "Stop Listening 🛑";
        };

        recognition.onresult = async (event) => {
            isListening = false;
            const text = event.results[0][0].transcript;
            if (userSpeech) userSpeech.innerText = text;
            if (statusText) statusText.innerText = "Processing response...";
            if (orbWrapper) orbWrapper.className = 'orb-wrapper';

            await sendToCalvis(text);
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            if (statusText) statusText.innerText = "Error recognizing speech. Tap to retry.";
            resetUI();
        };

        recognition.onend = () => {
            if (isListening) resetUI();
        };
    } else {
        if (statusText) statusText.innerText = "Web Speech API not supported in this browser.";
        if (talkBtn) talkBtn.disabled = true;
    }

    // 4. UI CONTROLS & STATE RESET
    function toggleListening() {
        if (!recognition) return;

        if (isListening) {
            recognition.stop();
            resetUI();
        } else {
            stopAllAudio(); // Halts active playback before starting microphone
            recognition.start();
        }
    }

    function resetUI() {
        isListening = false;
        if (orbWrapper) orbWrapper.className = 'orb-wrapper';
        if (statusText) statusText.innerText = "Tap orb to speak";
        if (talkBtn) {
            talkBtn.innerText = "Start Voice Session 🎙️";
            talkBtn.disabled = false;
        }
    }

    // 5. SERVER COMMUNICATION (Sends message to Flask backend)
    async function sendToCalvis(message) {
        if (talkBtn) talkBtn.disabled = true;
        if (aiReply) aiReply.innerText = "Calvis is thinking...";

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            if (data.reply) {
                if (aiReply) aiReply.innerText = data.reply;

                if (data.audio) {
                    playOnyxAudio(data.audio);
                } else {
                    resetUI();
                }
            } else {
                if (aiReply) aiReply.innerText = "Error: " + (data.error || "Failed to get response");
                resetUI();
            }
        } catch (err) {
            console.error("Fetch Error:", err);
            if (aiReply) aiReply.innerText = "Network error: Could not reach server.";
            resetUI();
        }
    }

    // 6. ONYX AUDIO STREAM PLAYER
    function playOnyxAudio(base64Audio) {
        stopAllAudio();

        currentAudio = new Audio("data:audio/mp3;base64," + base64Audio);

        currentAudio.onplay = () => {
            if (orbWrapper) orbWrapper.className = 'orb-wrapper speaking';
            if (statusText) statusText.innerText = "Calvis is speaking... 🗣️";
        };

        currentAudio.onended = () => {
            resetUI();
        };

        currentAudio.onerror = (e) => {
            console.error("Audio Playback Error:", e);
            resetUI();
        };

        currentAudio.play().catch(err => {
            console.error("Audio playback blocked by browser:", err);
            resetUI();
        });
    }

    // 7. EVENT LISTENERS
    if (orbWrapper) orbWrapper.addEventListener('click', toggleListening);
    if (talkBtn) talkBtn.addEventListener('click', toggleListening);
});
