document.addEventListener("DOMContentLoaded", () => {
    // 1. SELECT ALL HTML UI ELEMENTS Safely
    const orbWrapper = document.getElementById('orbWrapper');
    const statusText = document.getElementById('statusText');
    const talkBtn = document.getElementById('talkBtn');
    const userSpeech = document.getElementById('userSpeech');
    const aiReply = document.getElementById('aiReply');

    // 2. PRE-LOAD VOICES SYSTEM
    let voices = [];
    function loadVoices() {
        if ('speechSynthesis' in window) {
            voices = window.webkitSpeechSynthesis ? window.speechSynthesis.getVoices() : window.speechSynthesis.getVoices();
        }
    }
    
    loadVoices();
    if ('speechSynthesis' in window && window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    // 3. INITIALIZE WEB SPEECH API RECOGNITION
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        // When the microphone opens up successfully
        recognition.onstart = () => {
            isListening = true;
            if (orbWrapper) orbWrapper.className = 'orb-wrapper listening';
            if (statusText) statusText.innerText = "Listening... Speak now";
            if (talkBtn) talkBtn.innerText = "Stop Listening 🛑";
        };

        // When user stops speaking and the speech returns text
        recognition.onresult = async (event) => {
            isListening = false; // Toggle listener tracking back to false
            const text = event.results[0][0].transcript;
            if (userSpeech) userSpeech.innerText = text;
            if (statusText) statusText.innerText = "Processing response...";
            if (orbWrapper) orbWrapper.className = 'orb-wrapper';

            await sendToCalvis(text);
        };

        // Handle micro errors or dropouts cleanly
        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            if (statusText) statusText.innerText = "Error recognizing speech. Tap to retry.";
            resetUI();
        };

        // Clean termination setup
        recognition.onend = () => {
            if (isListening) {
                resetUI();
            }
        };
    } else {
        if (statusText) statusText.innerText = "Web Speech API not supported in this browser.";
        if (talkBtn) talkBtn.disabled = true;
    }

    // 4. CONTROL FUNCTIONS FOR USER INTERFACE
    function toggleListening() {
        if (!recognition) return;

        if (isListening) {
            recognition.stop();
            resetUI();
        } else {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); // Stop talking if currently speaking
            }
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

    // 5. SERVER COMMUNICATION (Asks Flask what to say back)
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
                speakBack(data.reply);
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

    // 6. TEXT TO SPEECH (Calvis talks out loud)
    function speakBack(text) {
        if (!('speechSynthesis' in window)) {
            resetUI();
            return;
        }

        window.speechSynthesis.cancel(); // Flush old utterance chains
        const utterance = new SpeechSynthesisUtterance(text);
        const activeVoices = voices.length ? voices : window.speechSynthesis.getVoices();

        // Find a natural fallback voice profile matching English criteria
        const warmVoice = activeVoices.find(v => 
            v.name.includes("Google US English") || 
            v.name.includes("Aria") || 
            v.name.includes("Natural") ||
            (v.lang === "en-US" && v.name.includes("Samantha"))
        );

        if (warmVoice) {
            utterance.voice = warmVoice;
        }

        utterance.pitch = 1.05;
        utterance.rate = 1.0;

        // UI states while talking out loud
        utterance.onstart = () => {
            if (orbWrapper) orbWrapper.className = 'orb-wrapper speaking';
            if (statusText) statusText.innerText = "Calvis is speaking... 🗣️";
        };

        utterance.onend = () => {
            resetUI();
        };

        utterance.onerror = () => {
            resetUI();
        };

        window.speechSynthesis.speak(utterance);
    }

    // 7. EVENT ACTION ATTACHMENTS
    if (orbWrapper) orbWrapper.addEventListener('click', toggleListening);
    if (talkBtn) talkBtn.addEventListener('click', toggleListening);
});
