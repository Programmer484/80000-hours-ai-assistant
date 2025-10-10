import json
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from config import MODEL_NAME, COLLECTION_NAME, EMBEDDING_DIM

load_dotenv()

def load_chunks(jsonl_path="article_chunks.jsonl"):
    chunks = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks

def create_qdrant_client():
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

def load_embedding_model():
    print("Loading embedding model...")
    return SentenceTransformer(MODEL_NAME)

def create_collection(client, collection_name=COLLECTION_NAME, embedding_dim=EMBEDDING_DIM):
    print(f"Creating collection '{collection_name}'...")
    try:
        if client.collection_exists(collection_name):
            print(f"Collection '{collection_name}' exists. Deleting...")
            client.delete_collection(collection_name)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
        )
        return True
    except Exception as e:
        print(f"Error creating collection: {e}")
        return False

def generate_embeddings(model, chunks):
    print("Generating embeddings...")
    texts = [chunk["text"] for chunk in chunks]
    return model.encode(texts, show_progress_bar=True)

def create_points(chunks, embeddings):
    points = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point = PointStruct(
            id=idx,
            vector=embedding.tolist(),
            payload={
                "url": chunk["url"],
                "title": chunk["title"],
                "date": chunk["date"],
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
            }
        )
        points.append(point)
    return points

def upload_points(client, points, collection_name=COLLECTION_NAME):
    print(f"Uploading {len(points)} points...")
    client.upsert(collection_name=collection_name, points=points)
    print(f"✓ Uploaded {len(points)} chunks to collection '{collection_name}'")

def verify_upload(client, collection_name=COLLECTION_NAME):
    collection_info = client.get_collection(collection_name)
    print(f"Collection now has {collection_info.points_count} points")
    return collection_info.points_count

def main():
    chunks = load_chunks()
    print(f"Found {len(chunks)} chunks")
    
    client = create_qdrant_client()
    model = load_embedding_model()
    
    if not create_collection(client):
        return
    
    embeddings = generate_embeddings(model, chunks)
    points = create_points(chunks, embeddings)
    upload_points(client, points)
    verify_upload(client)

if __name__ == "__main__":
    main()

