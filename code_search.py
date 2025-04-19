import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load all models and data
def load_all():
    model = SentenceTransformer("microsoft/codebert-base")
    index = faiss.read_index("code_embeddings.index")
    with open("code_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open("parsed_functions.json", "r", encoding="utf-8") as f:
        function_data = json.load(f)
    return model, index, metadata, function_data

def find_top_functions(question, model, index, function_data, k=3):
    lower_question = question.lower()
    name_matches = [
        i for i, func in enumerate(function_data)
        if any(word in func['function_name'].lower() for word in lower_question.split())
    ]

    query_embedding = model.encode([question])
    query_embedding = np.array(query_embedding).astype("float32")
    _, semantic_indices = index.search(query_embedding, k * 2)

    combined = name_matches + list(semantic_indices[0])
    unique_top_k = []
    for idx in combined:
        if idx not in unique_top_k:
            unique_top_k.append(idx)
        if len(unique_top_k) == k:
            break

    return unique_top_k

