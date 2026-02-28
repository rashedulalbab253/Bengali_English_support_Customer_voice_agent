import json
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types

from src.config import settings
from src.utils import logger

class CustomerSupportAgent:
    """Core logic for the AI Customer Support Agent with simple memory (using Gemini + Google Search Grounding)."""
    
    def __init__(self, api_key: Optional[str] = None):
        # Use provided API key or fallback to settings
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API Key is required for Gemini.")
        
        # Initialize the new Google GenAI client
        self.client = genai.Client(api_key=key)
        
        # System Instruction for Persona
        self.system_instruction = """You are an expert customer support AI for TechGadgets.com, a premium online electronics retailer.

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
- You have access to Google Search to find up-to-date product information, news, and pricing

Guidelines:
- Keep responses concise but complete (2-3 sentences ideal)
- Use a conversational, natural tone
- When answering about product availability, releases, or current pricing, rely on Google Search results for the most accurate and up-to-date information
- If you don't have specific information, acknowledge it honestly and offer to help in other ways
- Always end with a helpful follow-up question or offer when appropriate"""

        self.model_name = settings.GEMINI_MODEL
        self.app_id = settings.APP_ID
        
        # Google Search grounding tool
        self.google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Simple in-memory storage for conversations
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        logger.info("Agent initialized successfully with Gemini + Google Search Grounding.")

    def handle_query(self, query: str, user_id: str) -> str:
        """Handles a customer query using Gemini with Google Search grounding."""
        try:
            logger.info(f"Handling query for user {user_id}: {query[:50]}...")
            
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Build conversation history as Content objects for the new SDK
            history_contents = []
            history_slice = self.conversations[user_id][-10:]
            
            for msg in history_slice:
                role = "user" if msg["role"] == "user" else "model"
                # Ensure we start with 'user' and roles alternate
                if not history_contents:
                    if role != "user":
                        continue
                elif history_contents[-1].role == role:
                    # If same role as last, merge content
                    existing_text = history_contents[-1].parts[0].text
                    history_contents[-1].parts[0] = types.Part(text=f"{existing_text}\n{msg['content']}")
                    continue
                
                history_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            # Add the current user query
            history_contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=query)]
                )
            )
            
            # Configure with Google Search grounding and system instruction
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                tools=[self.google_search_tool],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE"
                    ),
                ]
            )

            # Generate response with grounding
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=history_contents,
                config=config,
            )
            
            answer = response.text
            
            # Log grounding metadata if available
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.web_search_queries:
                    logger.info(f"Google Search queries used: {metadata.web_search_queries}")
                if metadata.grounding_chunks:
                    sources = [chunk.web.title for chunk in metadata.grounding_chunks if chunk.web]
                    logger.info(f"Grounding sources: {sources}")
            
            # Update internal memory
            self.conversations[user_id].append({"role": "user", "content": query})
            self.conversations[user_id].append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Gemini Error: {str(e)}\n{error_trace}")
            # Log to file for deep inspection
            with open("error.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now()}] ERROR: {str(e)}\n{error_trace}\n")
            
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                return "⚠️ Rate limit exceeded! Your free tier quota is used up. Please wait a few minutes and try again, or enable billing at https://ai.google.dev. (⚠️ আপনার ফ্রি টিয়ার কোটা শেষ হয়ে গেছে। কয়েক মিনিট অপেক্ষা করুন।)"
            if "401" in str(e) or "API_KEY_INVALID" in str(e):
                return "Error: Invalid Gemini API Key. Please check your key and try again. (ত্রুটি: ভুল Gemini API কী। দয়া করে আপনার কী পরীক্ষা করুন এবং আবার চেষ্টা করুন।)"
            return f"I encountered an error with the AI: {str(e)}. Please check the logs."

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

            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            # Clean the response in case Gemini adds markdown formatting
            content = response.text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            customer_data = json.loads(content)
            
            # Store profile in conversation as context
            profile_msg = f"Customer Profile: {json.dumps(customer_data)}"
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            self.conversations[user_id].insert(0, {"role": "system", "content": profile_msg})

            return customer_data
        except Exception as e:
            logger.error(f"Profile generation failed: {e}")
            return None
