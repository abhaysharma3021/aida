from groq import Groq
import time
import os

class GroqClient:
    def __init__(self, model_name="meta-llama/llama-4-scout-17b-16e-instruct"):
        """
        Initialize the Groq client.
        
        Args:
            model_name (str): The model to use (default: llama3-8b-8192)
        """
        # Get API key from environment variables
        self.api_key = os.environ.get('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
            
        self.model_name = model_name
        self.client = Groq(api_key=self.api_key)
    
    def generate(self, prompt, system_prompt=None):
        """
        Generate a response using Groq.
        
        Args:
            prompt (str): The user prompt
            system_prompt (str, optional): The system prompt
            
        Returns:
            str: Generated response
        """
        try:
            # Prepare messages
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            print(f"Sending request to Groq for '{self.model_name}'...")
            
            # Send request to Groq
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            
            # Extract and return the response content
            return response.choices[0].message.content
                
        except Exception as e:
            error_msg = f"Error connecting to Groq API: {str(e)}"
            print(error_msg)
            return error_msg