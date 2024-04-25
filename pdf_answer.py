from flask import Flask, request, jsonify
from openai import OpenAI
from langchain.text_splitter import CharacterTextSplitter
import chromadb
import requests


# Initialize OpenAI client
openai_client = OpenAI(api_key="")

# Function to get embeddings
def get_embedding(text, client, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

# Function to split text into chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Function to perform semantic search
def semantic_search(query, text):
    embeddings = [get_embedding(i,openai_client) for i in get_text_chunks(text)]
    chroma_client = chromadb.Client()
    text_collection = chroma_client.get_or_create_collection("text")
    text_collection.add(
        embeddings=embeddings,
        documents=get_text_chunks(text),
        ids =[str(i) for i in range(len(embeddings))]
    )
    query_result = text_collection.query(
        query_embeddings=get_embedding(query, openai_client),
        n_results=10,
    )
    chroma_client.delete_collection(name="text")
    return query_result['documents'][0]

# Function to generate query output
def query_output(client, query):
    system_prompt = """You are given a user query along with the data which was retrieved from documents which user uploaded.
  Answer user query strictly based on this data and no other external knowledge.
  If you don't have knowledge regarding query say "Insufficient Data"
    """
    model = "gpt-3.5-turbo-1106"
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        )
        return completion.choices[0].message.content
    except requests.exceptions.RequestException as e:
        return f"Error making API request: {e}"


def process_text(text,query):

    # Perform semantic search
    similar_content = ' '.join(semantic_search(query, text))

    # Generate final user query
    final_user_query = "Query:" + query + "Retrieved data:" + similar_content

    # Get query output
    response = query_output(openai_client, final_user_query)

    return {'answer': response}

