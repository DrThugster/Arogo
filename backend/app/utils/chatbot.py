# backend/app/utils/chatbot.py
import google.generativeai as genai
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

class MedicalChatbot:
    def __init__(self):
        self.context = []
        self.initial_prompt = """
        You are a medical pre-diagnosis assistant. Your role is to:
        1. Ask relevant follow-up questions about symptoms
        2. Gather comprehensive information about the patient's condition
        3. Provide preliminary guidance and suggestions
        4. Recommend when to seek professional medical help
        
        Important rules:
        - Always maintain a professional and empathetic tone
        - Ask one question at a time
        - Don't make definitive diagnoses
        - Emphasize the importance of professional medical consultation
        - If symptoms are severe, immediately recommend seeking emergency care
        """

    async def process_message(self, message: str, user_details: Dict) -> str:
        """
        Process user message and generate response using Gemini API.
        """
        # Add user message to context
        self.context.append({"role": "user", "content": message})

        # Prepare context for Gemini
        context_text = self._prepare_context(user_details)

        try:
            # Generate response using Gemini
            response = model.generate_content([
                context_text,
                "\n\nCurrent user message: " + message,
                "\n\nProvide a helpful, relevant response:"
            ])

            # Process and format the response
            formatted_response = self._format_response(response.text)
            
            # Add response to context
            self.context.append({"role": "assistant", "content": formatted_response})

            return formatted_response

        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."

    def _prepare_context(self, user_details: Dict) -> str:
        """
        Prepare context for Gemini API including user details and conversation history.
        """
        context = self.initial_prompt + "\n\nPatient Details:\n"
        context += f"Age: {user_details['age']}\n"
        context += f"Gender: {user_details['gender']}\n"
        context += f"Previous conversation:\n"

        # Add last 5 exchanges for context
        for msg in self.context[-10:]:
            role = "Patient" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"

        return context

    def _format_response(self, response: str) -> str:
        """
        Format and clean the AI response.
        """
        # Remove any AI role-playing prefixes
        response = response.replace("Assistant:", "").replace("AI:", "").strip()

        # Ensure response doesn't make definitive diagnoses
        disclaimers = [
            "Based on the information provided, it seems",
            "Your symptoms might indicate",
            "It would be advisable to",
        ]

        for disclaimer in disclaimers:
            if disclaimer.lower() in response.lower():
                break
        else:
            response = "Based on the information provided, " + response

        return response

    def get_chat_summary(self) -> List[Dict]:
        """
        Return the chat history for summary generation.
        """
        return self.context