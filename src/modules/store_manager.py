import os
import pickle
from pathlib import Path
from typing import List, Dict, Any

from constants import OPEN_AI_API_KEY
from modules.embedding_types import embedding_types

from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import Chroma

persist_directory = "./vector_store/"

class store_manager:
    def __init__(self, embedding_type: embedding_types = embedding_types.HUGGINGFACEINSTRUCTEMBEDDINGS):
        self._embedding_type = embedding_type
        self._embedding_function = self.get_embeddings()
        self._vectorDb = Chroma(embedding_function=self._embedding_function, persist_directory=persist_directory)

    @property
    def store(self):
        return self._vectorDb

    def get_embeddings(self):
        if self._embedding_type == embedding_types.OPENAIEMBEDDINGS:
            return OpenAIEmbeddings(openai_api_key=OPEN_AI_API_KEY)
        else:
            return HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")

    def add(self, pdf_file_name: str, text_chunks: List[str]):
        self.delete(pdf_file_name=pdf_file_name)

        ids = [f"{pdf_file_name}_{index+1}" for index in range(len(text_chunks))]

        added_vector_ids = self._vectorDb.add_texts(texts=text_chunks, ids=ids, embedding=self._embedding_function, persist_directory=persist_directory)
        self._vectorDb.persist()

    def delete(self, pdf_file_name):
        for collection in self._vectorDb._client.list_collections():
            ids_to_delete = [id for id in collection.get()['ids'] if id.startswith(pdf_file_name)]
            if ids_to_delete: 
                print(f"deleting {len(ids_to_delete)} items")
                collection.delete(ids_to_delete)

        self._vectorDb.persist()