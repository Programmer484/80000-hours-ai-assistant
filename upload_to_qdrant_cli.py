import json
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from config import MODEL_NAME, COLLECTION_NAME, EMBEDDING_DIM

load_dotenv()

def load_chunks(jsonl_path="chunks.jsonl"):
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
    print("Initializing OpenAI client...")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def generate_embeddings(client, chunks):
    print("Generating embeddings via OpenAI...")
    texts = [chunk["text"] for chunk in chunks]
    
    # OpenAI recommends batching, maximum 2048 at a time for text-embedding-3
    embeddings = []
    batch_size = 500
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        print(f"  Embedding batch {i//batch_size + 1}...")
        response = client.embeddings.create(
            input=batch_texts,
            model=MODEL_NAME
        )
        embeddings.extend([data.embedding for data in response.data])
        
    return embeddings

def create_points(chunks, embeddings):
    points = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point = PointStruct(
            id=idx,
            vector=embedding,
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

def upload_points(client, points, collection_name=COLLECTION_NAME, batch_size=100):
    print(f"Uploading {len(points)} points in batches of {batch_size}...")
    total_batches = (len(points) + batch_size - 1) // batch_size
    
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        print(f"  Batch {batch_num}/{total_batches}: Uploading {len(batch)} points...")
        client.upsert(collection_name=collection_name, points=batch)
    
    print(f"✓ Uploaded {len(points)} chunks to collection '{collection_name}'")

def verify_upload(client, collection_name=COLLECTION_NAME):
    collection_info = client.get_collection(collection_name)
    print(f"Collection now has {collection_info.points_count} points")
    return collection_info.points_count

def ensure_collection_exists(client, collection_name=COLLECTION_NAME, embedding_dim=EMBEDDING_DIM):
    """Ensure collection exists, create if it doesn't. Returns starting ID for new points."""
    if not client.collection_exists(collection_name):
        print(f"Collection '{collection_name}' doesn't exist. Creating...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
        )
        return 0
    else:
        collection_info = client.get_collection(collection_name)
        point_count = collection_info.points_count
        print(f"Collection '{collection_name}' exists with {point_count} points")
        return point_count

def offset_point_ids(points, start_id):
    """Update point IDs to start from a given offset."""
    print(f"Setting point IDs starting from {start_id}...")
    for i, point in enumerate(points):
        point.id = start_id + i
    return points

def print_upload_summary(start_id, added_count, new_count):
    """Print upload summary statistics."""
    print(f"\n✓ Upload complete!")
    print(f"  Previous: {start_id} points")
    print(f"  Added: {added_count} points")
    print(f"  Total now: {new_count} points")

def upload_chunks_additive(chunks_file="chunks.jsonl"):
    """Upload chunks to Qdrant additively (preserves existing data)."""
    if not os.path.exists(chunks_file):
        print(f"Chunks file '{chunks_file}' not found")
        return
    
    chunks = load_chunks(chunks_file)
    print(f"Found {len(chunks)} chunks")
    
    if not chunks:
        print("No chunks to upload")
        return
    
    client = create_qdrant_client()
    start_id = ensure_collection_exists(client)
    
    model = load_embedding_model()
    embeddings = generate_embeddings(model, chunks)
    points = create_points(chunks, embeddings)
    points = offset_point_ids(points, start_id)
    
    upload_points(client, points)
    
    new_count = verify_upload(client)
    print_upload_summary(start_id, len(points), new_count)

def main():
    upload_chunks_additive()

if __name__ == "__main__":
    main()