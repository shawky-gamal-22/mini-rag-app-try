from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnum
import cohere 
import logging
from typing import List, Union

class CohereProvider(LLMInterface):

    def __init__(self, api_key: str,
                 default_input_max_characters: int=1000,
                 default_generation_max_output_tokens: int=1000,
                 default_generation_temperature: float=0.1):
        
        self.api_key = api_key
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.client = cohere.ClientV2(
            api_key=self.api_key
        )
        self.enums = CoHereEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        """
        Set the generation model to be used by the LLM.
        
        :param model_id: The identifier of the model to be set.
        """
        self.generation_model_id = model_id
        self.logger.info(f"Generation model set to {model_id}")

    def set_embedding_model(self, model_id: str, embedding_size: int):
        """
        Set the embedding model to be used by the LLM.
        
        :param model_id: The identifier of the embedding model to be set.
        :param embedding_size: The size of the embedding.
        """
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(f"Embedding model set to {model_id} with size {embedding_size}")


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
    
    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None,
                      temperature: float= None) -> str:
        if not self.client:
            self.logger.error("CoHere client is not initialized.")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model is not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature

        chat_history.append(self.construct_prompt(prompt=prompt,role=CoHereEnums.USER))
        response = self.client.chat(
            model = self.generation_model_id,
            messages=chat_history,
            temperature= temperature,
            max_tokens= max_output_tokens
        )

        if not response or not response.message.content[0].text:
            self.logger.error("Error while generating text with cohere")
            return None
        
        generated_text = response.message.content[0].text

        chat_history.append(self.construct_prompt(prompt=generated_text,role=CoHereEnums.ASSISTANT))
        
        return generated_text



    
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role.value if hasattr(role, "value") else role,
            "content": prompt
        }
    

    def embed_text(self, text: Union[str, List[str]], document_type: str= None) -> list:
        
        if not self.client:
            self.logger.error("CoHere client is not initialized.")
            return None
        
        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            self.logger.error("Embedding model is not set.")
            return None
        
        input_type = CoHereEnums.DOCUMENT

        if document_type == DocumentTypeEnum.QUERY:
            input_type = CoHereEnums.QUERY

        response = self.client.embed(
            model = self.embedding_model_id,
            texts = [ self.process_text(t) for t in text ],
            input_type = input_type,
            embedding_types = ['float']
        )

        if not response or not response.embeddings or not response.embeddings.float:
            self.logger.error("Error while embedding text with Cohere")
            return None
        
        
        return [f for f in response.embeddings.float]
         


