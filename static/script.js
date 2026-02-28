document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const apiKeyInput = document.getElementById('apiKey');
    const userIdInput = document.getElementById('userId');
    const initBtn = document.getElementById('initAgent');
    const genProfileBtn = document.getElementById('genProfile');
    const viewMemoriesBtn = document.getElementById('viewMemories');
    const agentStatus = document.getElementById('agentStatus');
    const statusIndicator = document.querySelector('.status-indicator');
    const profileDisplay = document.getElementById('profileDisplay');
    const profileJson = document.getElementById('profileJson');

    const micBtn = document.getElementById('micBtn');
    const autoSpeakCheck = document.getElementById('autoSpeak');
    const languageSelect = document.getElementById('languageSelect');
    const providerSelect = document.getElementById('providerSelect');
    const apiKeyLabel = document.getElementById('apiKeyLabel');

    if (providerSelect && apiKeyLabel && apiKeyInput) {
        providerSelect.addEventListener('change', () => {
            if (providerSelect.value === 'gemini') {
                apiKeyLabel.textContent = 'Google API Key';
                apiKeyInput.placeholder = 'AIzaSy...';
            } else {
                apiKeyLabel.textContent = 'Groq API Key';
                apiKeyInput.placeholder = 'gsk_...';
            }
        });
    }

    let initialized = false;
    let isRecording = false;

    // --- Voice Logic ---
    const recognition = window.SpeechRecognition || window.webkitSpeechRecognition ?
        new (window.SpeechRecognition || window.webkitSpeechRecognition)() : null;

    if (recognition) {
        recognition.continuous = false;
        recognition.interimResults = true;  // Show what's being said in real-time
        recognition.lang = languageSelect.value;
        recognition.maxAlternatives = 3;  // Get multiple interpretations

        languageSelect.addEventListener('change', () => {
            recognition.lang = languageSelect.value;
            console.log("Language changed to:", recognition.lang);
        });

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            updateStatus(true, languageSelect.value === 'bn-BD' ? 'শুনছি... (স্পষ্টভাবে বলুন)' : 'Listening... (speak clearly)');
            userInput.value = '';  // Clear input when starting
            userInput.placeholder = languageSelect.value === 'bn-BD' ? 'শুনছি...' : 'Listening...';
        };

        recognition.onend = () => {
            isRecording = false;
            micBtn.classList.remove('recording');
            updateStatus(true, 'Agent Online');
            userInput.placeholder = languageSelect.value === 'bn-BD' ? 'আপনার প্রশ্নটি বলুন...' : 'Ask about your orders, preferences...';
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            console.log("Interim:", interimTranscript);
            console.log("Final:", finalTranscript);

            // Show interim results in the input box
            if (interimTranscript) {
                userInput.value = interimTranscript;
                userInput.style.fontStyle = 'italic';
            }

            // When final, send the message
            if (finalTranscript.trim()) {
                userInput.value = finalTranscript.trim();
                userInput.style.fontStyle = 'normal';
                sendMessage();
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isRecording = false;
            micBtn.classList.remove('recording');
            updateStatus(true, 'Agent Online');

            if (event.error === 'no-speech') {
                userInput.placeholder = languageSelect.value === 'bn-BD' ? 'কোনো কথা শোনা যায়নি।' : 'No speech detected. Try again.';
            } else if (event.error === 'audio-capture') {
                alert('Microphone not found. Please check your microphone settings.');
            } else if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access.');
            }
        };
    }

    const speak = (text) => {
        if (!autoSpeakCheck.checked) return;

        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = languageSelect.value;
        utterance.rate = 0.95;  // Slightly slower for clarity
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Wait for voices to load, then select the best one
        const setVoice = () => {
            const voices = window.speechSynthesis.getVoices();
            let selectedVoice = null;

            if (languageSelect.value === 'bn-BD') {
                // Try to find a Bengali voice
                selectedVoice = voices.find(v => v.lang.startsWith('bn'));
            } else {
                // Prefer English voices
                const preferredVoices = [
                    'Google US English',
                    'Microsoft Zira',
                    'Microsoft David',
                    'Google UK English Female',
                    'Samantha',
                    'Alex'
                ];

                for (const preferred of preferredVoices) {
                    selectedVoice = voices.find(v => v.name.includes(preferred));
                    if (selectedVoice) break;
                }

                if (!selectedVoice) {
                    selectedVoice = voices.find(v => v.lang.startsWith('en'));
                }
            }

            if (selectedVoice) {
                utterance.voice = selectedVoice;
            }

            window.speechSynthesis.speak(utterance);
        };

        // Voices might not be loaded yet
        if (window.speechSynthesis.getVoices().length > 0) {
            setVoice();
        } else {
            window.speechSynthesis.onvoiceschanged = setVoice;
        }
    };

    // --- Helper Functions ---

    const addMessage = (role, text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        msgDiv.innerHTML = `<div class="bubble">${text}</div>`;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const updateStatus = (online, message) => {
        initialized = online;
        agentStatus.textContent = message;
        if (online) {
            statusIndicator.classList.add('online');
        } else {
            statusIndicator.classList.remove('online');
        }
    };

    // --- API Calls ---

    const initializeAgent = async () => {
        const apiKey = apiKeyInput.value.trim();
        const userId = userIdInput.value.trim();
        const lang = languageSelect.value;
        const provider = providerSelect ? providerSelect.value : 'groq';

        if (!apiKey || !userId) {
            alert(`Please provide both ${provider === 'gemini' ? 'Google' : 'Groq'} API Key and Customer ID`);
            return;
        }

        updateStatus(false, lang === 'bn-BD' ? 'সংযুক্ত হচ্ছে...' : 'Connecting...');

        updateStatus(true, 'Agent Online');

        const welcomeMsg = lang === 'bn-BD'
            ? `OmniServe AI গ্রাহক <strong>${userId}</strong> এর জন্য প্রস্তুত। আমি আপনাকে কীভাবে সাহায্য করতে পারি?`
            : `OmniServe AI initialized for customer: <strong>${userId}</strong>. How can I help you?`;

        addMessage('assistant', welcomeMsg);
    };

    const sendMessage = async () => {
        const text = userInput.value.trim();
        const userId = userIdInput.value.trim();
        const apiKey = apiKeyInput.value.trim();

        if (!text) return;
        if (!initialized) {
            alert('Please initialize the agent first');
            return;
        }

        addMessage('user', text);
        userInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, user_id: userId, api_key: apiKey, provider: providerSelect ? providerSelect.value : 'groq' })
            });
            const data = await response.json();
            console.log("Server Response:", data);

            if (data.response) {
                addMessage('assistant', data.response);
                speak(data.response);
            } else if (data.detail) {
                addMessage('assistant', `Error: ${data.detail}`);
            } else {
                addMessage('assistant', "Error: Received undefined response from server.");
            }
        } catch (error) {
            addMessage('assistant', 'Error: Could not reach the server.');
        }
    };

    const generateProfile = async () => {
        const userId = userIdInput.value.trim();
        const apiKey = apiKeyInput.value.trim();

        if (!initialized) {
            alert('Please initialize first');
            return;
        }

        try {
            updateStatus(true, 'Generating Profile...');
            const response = await fetch('/generate-profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, api_key: apiKey, provider: providerSelect ? providerSelect.value : 'groq' })
            });
            const data = await response.json();
            profileDisplay.classList.remove('hidden');
            profileJson.textContent = JSON.stringify(data, null, 2);
            updateStatus(true, 'Agent Online');
            alert('Synthetic profile generated and added to memory!');
        } catch (error) {
            alert('Failed to generate profile');
            updateStatus(true, 'Agent Online');
        }
    };

    const fetchMemories = async () => {
        const userId = userIdInput.value.trim();
        if (!userId) {
            alert('Enter User ID first');
            return;
        }

        try {
            const response = await fetch(`/memories/${userId}`);
            const data = await response.json();

            const modal = document.getElementById('memoryModal');
            const list = document.getElementById('memoryList');
            list.innerHTML = '';

            if (data.memories.length === 0) {
                list.innerHTML = '<li>No memories found for this user.</li>';
            } else {
                data.memories.forEach(m => {
                    const li = document.createElement('li');
                    li.textContent = m;
                    list.appendChild(li);
                });
            }

            modal.classList.remove('hidden');
        } catch (error) {
            alert('Failed to fetch memories');
        }
    };

    const fetchAnalytics = async () => {
        try {
            const response = await fetch('/analytics/summary');
            const data = await response.json();

            document.getElementById('totalInteractions').textContent = data.total_interactions;
            document.getElementById('uniqueUsers').textContent = data.unique_users;
            document.getElementById('avgResponseTime').textContent = `${data.avg_response_time}s`;
            document.getElementById('avgQueryLength').textContent = Math.round(data.avg_query_length);

            // Fetch top users
            const topUsersResponse = await fetch('/analytics/top-users');
            const topUsersData = await topUsersResponse.json();
            const topUsersList = document.getElementById('topUsersList');
            topUsersList.innerHTML = '';

            if (topUsersData.top_users.length === 0) {
                topUsersList.innerHTML = '<li>No data yet</li>';
            } else {
                topUsersData.top_users.forEach(user => {
                    const li = document.createElement('li');
                    li.textContent = `${user.user_id}: ${user.total_queries} queries`;
                    topUsersList.appendChild(li);
                });
            }

            // Fetch recent interactions
            const recentResponse = await fetch('/analytics/recent?limit=5');
            const recentData = await recentResponse.json();
            const recentDiv = document.getElementById('recentInteractions');
            recentDiv.innerHTML = '';

            if (recentData.interactions.length === 0) {
                recentDiv.innerHTML = '<p>No interactions yet</p>';
            } else {
                recentData.interactions.forEach(interaction => {
                    const card = document.createElement('div');
                    card.className = 'interaction-card';

                    const safeQuery = (interaction.query || "").substring(0, 50);
                    const safeResponse = (interaction.response || "").substring(0, 50);
                    const safeUser = interaction.user_id || "Anonymous";
                    const safeTime = typeof interaction.response_time === 'number' ? interaction.response_time.toFixed(2) : "0.00";

                    card.innerHTML = `
                        <strong>${safeUser}</strong>
                        <p><em>Q:</em> ${safeQuery}...</p>
                        <p><em>A:</em> ${safeResponse}...</p>
                        <small>${safeTime}s</small>
                    `;
                    recentDiv.appendChild(card);
                });
            }

            document.getElementById('analyticsModal').classList.remove('hidden');
        } catch (error) {
            alert('Failed to fetch analytics');
        }
    };

    // --- Event Listeners ---

    initBtn.addEventListener('click', initializeAgent);
    sendBtn.addEventListener('click', sendMessage);

    micBtn.addEventListener('click', () => {
        if (!recognition) {
            alert('Speech recognition is not supported in this browser.');
            return;
        }
        if (isRecording) {
            recognition.stop();
        } else {
            // Set language right before starting to ensure it's current
            recognition.lang = languageSelect.value;
            console.log("Starting recognition with language:", recognition.lang);
            recognition.start();
        }
    });

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    genProfileBtn.addEventListener('click', generateProfile);
    viewMemoriesBtn.addEventListener('click', fetchMemories);
    document.getElementById('viewAnalytics').addEventListener('click', fetchAnalytics);

    // Modal close
    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('memoryModal').classList.add('hidden');
    });

    document.querySelector('.close-analytics').addEventListener('click', () => {
        document.getElementById('analyticsModal').classList.add('hidden');
    });

    // Clear chat
    document.getElementById('clearChat').addEventListener('click', () => {
        chatMessages.innerHTML = '';
        addMessage('assistant', 'Chat cleared.');
    });
});
