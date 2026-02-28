import json
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.config import settings
from src.utils import logger
from src.web_search import search_web, format_search_context, needs_web_search

# System instruction shared by both providers
SYSTEM_INSTRUCTION = """You are an expert customer support AI for TechGadgets.com, a premium online electronics retailer.

Language Support:
- You must respond ONLY in the same language the user uses.
- If the user speaks in Bengali, respond in Bengali.
- If the user speaks in English, respond in English.
- Your personality should remain consistent across languages.

Your personality:
- Professional yet warm and friendly
- Patient and empathetic
- Solution-oriented
- Knowledgeable about tech products

Your capabilities:
- Help with order tracking, returns, and product recommendations
- Troubleshoot technical issues
- Answer questions about warranties and shipping
- Remember conversation context to provide personalized help
- You have access to real-time web search results to provide up-to-date product information

IMPORTANT - Current Product Knowledge (as of March 2026):
Your training data may be outdated. ALWAYS use the following up-to-date information when answering about recent products:
- Apple iPhone 17 series: RELEASED in September 2025. Models include iPhone 17, iPhone 17 Air, iPhone 17 Pro, and iPhone 17 Pro Max. Available for purchase now at TechGadgets.com.
- Samsung Galaxy S25 series: RELEASED in January 2025.
- Google Pixel 9 series: RELEASED in August 2024.

CRITICAL RULE: If a customer asks about any of the products listed above, you MUST use the information provided here. Do NOT say a product "has not been released" or "is not available yet" if it is listed above as RELEASED.

Guidelines:
- Keep responses concise but complete (2-3 sentences ideal)
- Use a conversational, natural tone
- When web search results are provided, use them to give accurate and current information
- If you don't have specific information, acknowledge it honestly and offer to help in other ways
- Always end with a helpful follow-up question or offer when appropriate"""


class CustomerSupportAgent:
    """Core logic for the AI Customer Support Agent with dual provider support (Gemini + Groq)."""
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        self.app_id = settings.APP_ID
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        
        if self.provider == "gemini":
            self._init_gemini(api_key)
        elif self.provider == "groq":
            self._init_groq(api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Use 'gemini' or 'groq'.")
        
        logger.info(f"Agent initialized successfully with provider: {self.provider}")

    def _init_gemini(self, api_key: Optional[str] = None):
        """Initialize Gemini with Google Search grounding."""
        from google import genai
        from google.genai import types
        
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API Key is required for Gemini.")
        
        self.client = genai.Client(api_key=key)
        self.model_name = settings.GEMINI_MODEL
        self.google_search_tool = types.Tool(google_search=types.GoogleSearch())

    def _init_groq(self, api_key: Optional[str] = None):
        """Initialize Groq with web search grounding."""
        from groq import Groq
        
        key = api_key or settings.GROQ_API_KEY
        if not key:
            raise ValueError("Groq API Key is required.")
        
        self.groq_client = Groq(api_key=key)
        self.groq_model = settings.GROQ_MODEL

    def handle_query(self, query: str, user_id: str) -> str:
        """Routes to the appropriate provider's handler."""
        if self.provider == "gemini":
            return self._handle_gemini(query, user_id)
        else:
            return self._handle_groq(query, user_id)

    def _handle_gemini(self, query: str, user_id: str) -> str:
        """Handle query using Gemini with Google Search grounding."""
        from google.genai import types
        
        try:
            logger.info(f"[Gemini] Handling query for user {user_id}: {query[:50]}...")
            
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Build conversation history
            history_contents = []
            history_slice = self.conversations[user_id][-10:]
            
            for msg in history_slice:
                role = "user" if msg["role"] == "user" else "model"
                if not history_contents:
                    if role != "user":
                        continue
                elif history_contents[-1].role == role:
                    existing_text = history_contents[-1].parts[0].text
                    history_contents[-1].parts[0] = types.Part(text=f"{existing_text}\n{msg['content']}")
                    continue
                
                history_contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg["content"])])
                )

            history_contents.append(
                types.Content(role="user", parts=[types.Part(text=query)])
            )
            
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[self.google_search_tool],
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=history_contents,
                config=config,
            )
            
            answer = response.text
            
            # Log grounding metadata
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.web_search_queries:
                    logger.info(f"Google Search queries: {metadata.web_search_queries}")
                if metadata.grounding_chunks:
                    sources = [chunk.web.title for chunk in metadata.grounding_chunks if chunk.web]
                    logger.info(f"Grounding sources: {sources}")
            
            self.conversations[user_id].append({"role": "user", "content": query})
            self.conversations[user_id].append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            return self._handle_error(e)

    def _handle_groq(self, query: str, user_id: str) -> str:
        """Handle query using Groq with DuckDuckGo web search grounding."""
        try:
            logger.info(f"[Groq] Handling query for user {user_id}: {query[:50]}...")
            
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Build messages for Groq (OpenAI-compatible format)
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            
            # Add conversation history (last 10 messages)
            history_slice = self.conversations[user_id][-10:]
            for msg in history_slice:
                role = msg["role"]
                if role == "assistant":
                    role = "assistant"
                messages.append({"role": role, "content": msg["content"]})
            
            # Perform web search if the query needs current information
            search_context = ""
            if needs_web_search(query):
                logger.info(f"Query needs web search: {query[:50]}...")
                search_results = search_web(query, max_results=5)
                search_context = format_search_context(search_results)
                
                if search_context:
                    logger.info(f"Web search returned {len(search_results)} results")
                    # Add search context as a system message right before the user query
                    messages.append({
                        "role": "system",
                        "content": search_context
                    })
            
            # Add current user query
            messages.append({"role": "user", "content": query})
            
            # Call Groq API
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            answer = response.choices[0].message.content
            
            # Log search usage
            if search_context:
                logger.info(f"[Groq] Response generated with web search grounding")
            else:
                logger.info(f"[Groq] Response generated without web search")
            
            # Update internal memory
            self.conversations[user_id].append({"role": "user", "content": query})
            self.conversations[user_id].append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            return self._handle_error(e)

    def _handle_error(self, e: Exception) -> str:
        """Centralized error handling for both providers."""
        error_trace = traceback.format_exc()
        logger.error(f"AI Error: {str(e)}\n{error_trace}")
        
        with open("error.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] ERROR: {str(e)}\n{error_trace}\n")
        
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "rate_limit" in error_str.lower():
            return "⚠️ Rate limit exceeded! Please wait a few minutes and try again. (⚠️ রেট লিমিট অতিক্রম হয়েছে। কয়েক মিনিট অপেক্ষা করুন।)"
        if "401" in error_str or "API_KEY_INVALID" in error_str or "invalid_api_key" in error_str.lower():
            return "Error: Invalid API Key. Please check your key and try again. (ত্রুটি: ভুল API কী। দয়া করে পরীক্ষা করুন।)"
        return f"I encountered an error: {str(e)}. Please check the logs."

    def get_user_memories(self, user_id: str) -> List[str]:
        """Retrieves conversation history for a user."""
        try:
            if user_id in self.conversations:
                return [f"{msg['role']}: {msg['content']}" for msg in self.conversations[user_id]]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch memories for {user_id}: {e}")
            return []

    def generate_synthetic_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Generates a realistic customer profile."""
        try:
            logger.info(f"Generating synthetic profile for user {user_id}")
            today = datetime.now()
            order_date = (today - timedelta(days=10)).strftime("%B %d, %Y")
            expected_delivery = (today + timedelta(days=2)).strftime("%B %d, %Y")

            prompt = f"""Generate a detailed JSON customer profile for ID {user_id}. Include:
            - Basic Info (Name, Email)
            - Recent high-end electronics order (Placed: {order_date}, Delivery: {expected_delivery})
            - 2 past orders and 2 previous support interactions.
            Return ONLY valid JSON."""

            if self.provider == "gemini":
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                content = response.text
            else:
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Return ONLY valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1024,
                )
                content = response.choices[0].message.content

            # Clean markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            customer_data = json.loads(content)
            
            profile_msg = f"Customer Profile: {json.dumps(customer_data)}"
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            self.conversations[user_id].insert(0, {"role": "system", "content": profile_msg})

            return customer_data
        except Exception as e:
            logger.error(f"Profile generation failed: {e}")
            return None
