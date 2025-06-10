import os 
import shutil
import subprocess
from ghostcoder.config import *

from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings 
from langchain_community.embeddings import DashScopeEmbeddings


def setup_LLMs():
    try:
        chat_model = ChatOpenAI(
            api_key = llm_api_config.CHAT_MODEL_API['api'],
            base_url= llm_api_config.CHAT_MODEL_API['url'],
            model = llm_api_config.CHAT_MODEL_API['model'],
            temperature= 0,
            max_retries = 3,
            )
    except:
        chat_model = None

    llm_api_config.MODELS['chat_model'] = chat_model

    try:
        code_model = ChatOpenAI(
            api_key = llm_api_config.CODE_MODEL_API['api'],
            base_url= llm_api_config.CODE_MODEL_API['url'],
            model = llm_api_config.CODE_MODEL_API['model'],
            temperature= 0,
            max_retries = 3,
            )
    except:
        code_model = None

    llm_api_config.MODELS['code_model'] = code_model

    try:
        embed_model = DashScopeEmbeddings(
            dashscope_api_key = llm_api_config.EMBED_MODEL_API['api'],
            model = llm_api_config.EMBED_MODEL_API['model'],
            )
    except:
        try: 
            embed_model = OpenAIEmbeddings(
                api_key = llm_api_config.EMBED_MODEL_API['api'],
                base_url= llm_api_config.EMBED_MODEL_API['url'],
                model = llm_api_config.EMBED_MODEL_API['model'],
                )
        except:
            embed_model = None

    llm_api_config.MODELS['embed_model'] = embed_model



    
def setup_RefCodeDB(
        emb_model, 
        port: int=6688,
        name: str="RefCodeDB",
        search_type: str = "mmr",
        n_res: int = 5,
        ):

    # Connect to Docker Postgres
    connection = "postgresql+psycopg://Refcodedb:Refcodedb@localhost:"+str(port)+"/RefCodeDB"  

    vector_store = PGVector(
        embeddings=emb_model,
        collection_name=name,
        connection=connection,
        use_jsonb=True,
    )

    retriever = vector_store.as_retriever(
        search_type=search_type, 
        search_kwargs={"k": n_res})
    
    return retriever

def setup_vdbs(name, emb_model):
    if name == "RefCodeDB":
        retriever = setup_RefCodeDB(emb_model)
    return retriever