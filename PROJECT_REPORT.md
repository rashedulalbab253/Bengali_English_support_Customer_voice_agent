# Project Report & Interview Prep Guide: OmniServe AI
## Professional Context-Aware Real-Time Voice Customer Support Platform

**Author:** Rashedul Albab  
**Date:** March 2026  
**Status:** Completed - Production Ready  
**Category:** Artificial Intelligence / Conversational AI / Full-Stack Engineering 
**Live Demo:** https://customer-support-voce-agent.onrender.com/ 

---

## 1. Executive Summary
**OmniServe AI** is a state-of-the-art, voice-enabled customer support platform designed to bridge the gap between human empathy and AI efficiency. By utilizing large language models (LLMs) and real-time audio processing, OmniServe AI provides a seamless, context-aware experience that remembers user preferences and history. The final implementation features a professional **Enterprise Modern UI** that is fully **Mobile-Responsive** and utilizes advanced LLMs (like **Google Gemini** and **Groq**) for localized, multilingual (English/Bengali) conversational intelligence.

---

## 2. Technical Architecture & Tech Stack

### 2.1 Technology Stack (The "Why")
- **Backend**: **FastAPI** (Python)
  - *Why?* Extremely fast, natively async (crucial for I/O bound LLM network calls), and provides automatic API documentation (Swagger/OpenAPI).
- **AI Core**: **Google Gemini & Groq APIs**
  - *Why?* Gemini provides excellent multilingual support (crucial for Bengali), while Groq provides ultra-low latency inference for Llama models.
- **Frontend**: **Vanilla JavaScript (ES6+), HTML5, CSS3**
  - *Why?* Zero-dependency architecture keeps the footprint incredibly small, ensuring blazing fast load times globally.
- **Voice Engine**: **Web Speech API**
  - *Why?* Native browser API means no heavy audio processing on the backend, saving server costs and providing instant transcription on the client-side.
- **DevOps**: **Docker & Docker Compose**
  - *Why?* Containerization ensures the "it works on my machine" problem is eliminated, allowing for seamless deployment to platforms like Render.

### 2.2 Detailed System Architecture & Data Flow Workflow

The architecture is divided into decoupled micro-components that ensure strict separation of concerns, scalability, and latency optimization.

**1. Client Layer (Frontend UI & Voice Processing)**
- **Input Capture**: The UI leverages the native browser `Web Speech API` to capture microphone streams. This processes audio continuously (chunk by chunk) and converts it to text locally on the user's device.
- **Interim Feedback**: As the user speaks, interim text results are displayed in real-time (`interimResults=true`), significantly improving perceived latency.
- **Request Dispatch**: Once speech ends (or text is typed), an asynchronous `POST` request (`/chat`) containing the payload (query, user ID, API key, selected provider, language) is dispatched to the backend.

**2. API Gateway & Routing (FastAPI Backend)**
- **Asynchronous Ingestion**: The FastAPI server receives the request. As it is built on Starlette and Pydantic, it immediately validates the incoming JSON payload schema.
- **Provider Routing**: The router evaluates the requested LLM provider (`Groq` or `Gemini`) and sets up the appropriate API client configuration dynamically.

**3. Context & Memory Management Module (`agent.py`)**
- **Profile Injection**: The system retrieves the user's generated synthetic profile (containing simulated data like past orders, account status, and preferences).
- **Conversational Memory**: The `MemoryManager` fetches a sliding window of the last `N` interactions (e.g., the last 5 Q&A pairs) linked to the specific `user_id` in order to maintain a stateless backend while preserving user context.
- **Prompt Construction**: A highly engineered System Prompt is compiled on the fly. It systematically injects:
  1. The Expert Persona (instructions on boundaries and tone).
  2. The User Profile (factual grounding data to prevent hallucinations).
  3. The Chat History (contextual awareness).
  4. The Current Query.

**4. Intelligence Engine (LLM Inference)**
- **Non-Blocking API Call**: The constructed prompt is sent to the selected LLM provider via asynchronous HTTP calls (`asyncio`). This ensures the FastAPI event loop is never blocked, allowing a single server thread to handle hundreds of concurrent users without waiting for the LLM to generate tokens.
- **Response Generation**: The LLM processes the query and returns the generated text response, adhering strictly to the requested language (English or Bengali).

**5. Post-Processing & Analytics Module**
- **Metrics Calculation**: The application calculates critical UX metrics such as end-to-end response latency (time taken for the API call) and query character length.
- **Data Delivery**: The final text string is sent back to the client UI as a JSON response.
- **Asynchronous Logging**: Using FastAPI background tasks or post-response hooks, the interaction is logged into the `analytics` store. This eliminates database write bottlenecks.

**6. Client Output (Text-to-Speech)**
- **Display**: The response is instantly rendered in the chat interface with an entry animation.
- **Synthesis**: If 'auto-speak' is toggled on, the browser's `SpeechSynthesis API` converts the text back into voice, dynamically selecting an appropriate localized voice profile stack (e.g., falling back to native Bengali voices) to complete the multimodal interaction loop.

---

## 3. Key Features & Implementation

### 3.1 Multilingual Conversational Intelligence
The platform provides robust, native support for English and Bengali. The AI detects the predefined language context and adheres to a strict "Expert Persona", ensuring a localized and culturally aware experience for diverse markets.

### 3.2 Mobile-Responsive Enterprise UI
Departing from generic templates, OmniServe AI utilizes a highly polished aesthetic:
- **Responsive Layout**: Designed mobile-first. Features a secure off-canvas absolute-positioned sidebar on devices under 768px, ensuring the chat interface utilizes 100% of available mobile screen real estate.
- **Design System**: Indigo secondary focus (#4f46e5) with Inter and Outfit typography for sharp readability.

### 3.3 Contextual Persistence & Synthetic Data
The system dynamically generates "Mock Profiles" using AI to simulate complex customer histories. This allows the agent to recall past orders, shipping addresses, and preferences contextually without requiring a heavy real-time database connection during the prototype phase.

---

## 4. 🚀 INTERVIEW PREPARATION (Q&A Section)
*Use these points to confidently answer technical questions during your interviews.*

### Q1: "Walk me through a challenging problem you faced while building OmniServe AI and how you solved it."
**Answer (STAR Method):**
- **Situation**: I needed to implement real-time voice recognition that felt instantaneous and also supported both English and Bengali natively.
- **Task**: Relying on the backend to process audio files via Whisper or similar APIs was creating huge latency (3-5 seconds), breaking the conversational illusion.
- **Action**: I pivoted the architecture to utilize the browser's native **Web Speech API**. I customized the JavaScript frontend to capture streams, configured the `lang` attribute dynamically based on user selection (`bn-BD` or `en-US`), and utilized `interimResults=true` to provide real-time visual feedback to the user as they spoke.
- **Result**: Transcription latency dropped to effectively zero since it happens client-side, heavily reducing backend server load and massively improving the UX. 

### Q2: "How did you ensure your application is scalable?"
**Answer:**
- "I designed the backend using **FastAPI** specifically because of its asynchronous capabilities. When the backend makes a network call to the LLM (API), the server thread isn't blocked. It can handle hundreds of concurrent users while waiting for Google or Groq to respond. Furthermore, the entire application is completely **Dockerized**. We can spin up multiple stateless containers behind a load balancer instantly, which I successfully demonstrated by deploying to Render."

### Q3: "I see you built the frontend with Vanilla JavaScript instead of React. Why?"
**Answer:**
- "For this specific platform, the core requirement was speed and direct DOM manipulation for the Web Speech APIs. By sticking to Vanilla JS and CSS3, I avoided the overhead and bundle size of a virtual DOM framework. It allowed me to deliver a blazing-fast initial page load, and gave me fine-grained control over UI micro-interactions, like the mobile sidebar toggle and the pulsing microphone animation which might have been more complex to wire up with React states."

### Q4: "How does your system handle memory and context?"
**Answer:**
- "LLMs are stateless by nature. I engineered a contextual memory manager inside `agent.py`. For a given user session, I maintain a sliding window of the most recent conversational turns (e.g., last 10 messages). I compile this history alongside the user's specific 'Profile Metadata' into a master system prompt before sending it to the LLM. This guarantees the AI 'remembers' the user's past orders and current issues without exceeding the token limit."

### Q5: "How did you approach mobile responsiveness?"
**Answer:**
- "I implemented a **mobile-first responsive design** using CSS media queries. The biggest challenge was the dense desktop layout containing the settings sidebar and the chat interface. For screens under `768px`, I refactored the sidebar to use `absolute` positioning, sliding it off-canvas (`left: -320px`). I introduced a custom hamburger menu in the chat header and a semi-transparent dark overlay to toggle the sidebar on demand, maintaining a clean chat view for phone users."

---

*© 2026 OmniServe AI. Project Developed & Designed by Rashedul Albab.*
