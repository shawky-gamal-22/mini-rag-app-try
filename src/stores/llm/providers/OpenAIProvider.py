from ..LLMInterface import LLMInterface
from openai import OpenAI
import logging
from ..LLMEnums import OpenAIEnum
from typing import List, Union

class OpenAIProvider(LLMInterface):

    def __init__(self, api_key: str, api_url: str=None,
                 default_input_max_characters: int=1000,
                 default_generation_max_output_tokens: int=1000,
                 default_generation_temperature: float=0.1):
        self.api_key = api_key
        self.api_url = api_url
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.client = OpenAI(api_key=self.api_key,
                             base_url=self.api_url if self.api_url and len(self.api_url) else None
                             )
        self.enums = OpenAIEnum
        self.logger = logging.getLogger(__name__)

    
    def set_generation_model(self, model_id: str):
        
        self.generation_model_id = model_id
        self.logger.info(f"Generation model set to {model_id}")

    def set_embedding_model(self, model_id: str, embedding_size: int):
        
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(f"Embedding model set to {model_id} with size {embedding_size}")

    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None,
                      temperature: float= None) -> str:
        
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model is not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature
        chat_history.append(self.construct_prompt(prompt=prompt, role= OpenAIEnum.USER.value))

        response = self.client.chat.completions.create(
            model = self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )
        if (
            not response
            or not hasattr(response, "choices")
            or not response.choices
            or not hasattr(response.choices[0], "message")
            or not hasattr(response.choices[0].message, "content")
            or not response.choices[0].message.content
        ):
            self.logger.error("Failed to generate text.")
            return None
        
        generated_text = response.choices[0].message.content
        chat_history.append(self.construct_prompt(prompt=generated_text, role=OpenAIEnum.ASSISTANT.value))
        self.logger.info(f"Generated text: {generated_text}")
        return generated_text



    def embed_text(self, text: Union[str, List[str]], document_type: str= None) -> list:
        if not self.embedding_model_id:
            raise ValueError("Embedding model is not set.")
        
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        respose = self.client.embeddings.create(
            model=self.embedding_model_id,
            input=text,
            
        )
        if not respose or not respose.data or len(respose.data) == 0 or not respose.data[0].embedding:
            self.logger.error("Failed to generate embedding.")
            return None
        

        return [rec.embedding for rec in respose.data]
    
    
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt
        }
    

    def process_text(self, text: str) -> str:
        """
        Process the input text to ensure it meets the requirements of the LLM.
        
        :param text: The input text to be processed.
        :return: The processed text.
        """
        if len(text) > self.default_input_max_characters:
            self.logger.warning(f"Input text exceeds maximum length of {self.default_input_max_characters} characters.")
            return text[:self.default_input_max_characters]
        
        return text.strip()


     
        
        
