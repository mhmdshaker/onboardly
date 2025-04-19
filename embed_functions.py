import os
import json
import numpy as np
import gc  # Garbage collection
from sentence_transformers import SentenceTransformer
import faiss

# Global variable to store the model
_model = None

def get_model():
    global _model
    if _model is None:
        print("📥 Loading CodeBERT embedding model...")
        # Set environment variables to limit memory usage
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        _model = SentenceTransformer("microsoft/codebert-base")
    return _model

def embed_parsed_functions():
    # Load functions from JSON
    with open("parsed_functions.json", "r", encoding="utf-8") as f:
        functions = json.load(f)
    
    if not functions:
        print("⚠️ No functions found to embed.")
        return
    
    # Get text representations to encode
    function_texts = []
    for func in functions:
        # Include function name, signature and docstring in embedding
        signature = f"{func['function_name']}({', '.join(func['args'])})"
        docstring = func['docstring'] if func['docstring'] else ""
        function_texts.append(f"{signature}\n{docstring}\n{func['code']}")
    
    try:
        # Get model and create embeddings
        model = get_model()
        
        embeddings = model.encode(
        function_texts,
        batch_size=4,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
        
        # Limit batch size to avoid memory issues
        print(f"🧠 Creating embeddings for {len(function_texts)} functions...")
        embeddings = model.encode(function_texts, batch_size=4, show_progress_bar=True)
        
        # Force garbage collection before FAISS operations
        gc.collect()
        
        print("📊 Creating FAISS index...")
        # Create FAISS index - use a simpler index type
        dimension = embeddings.shape[1]
        
        # Convert to float32 before any FAISS operations
        embeddings = embeddings.astype('float32')
        
        # Create index
        index = faiss.IndexFlatL2(dimension)
        
        # Normalize embeddings
        print("🔄 Normalizing embeddings...")
        faiss.normalize_L2(embeddings)
        
        # Add to index
        print("➕ Adding embeddings to index...")
        index.add(embeddings)
        
        # Save index and metadata
        print("💾 Saving FAISS index...")
        faiss.write_index(index, "code_embeddings.index")
        
        # Clear memory
        del embeddings
        del index
        gc.collect()
        
        # Save metadata mapping the index positions to function data
        print("📝 Saving metadata...")
        metadata = [
            {
                "index": i,
                "function_name": func["function_name"],
                "file": func["file"]
            }
            for i, func in enumerate(functions)
        ]
        
        with open("code_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print("✅ Embeddings created and saved.")
    except Exception as e:
        print(f"❌ Error creating embeddings: {str(e)}")
        # Print the full error traceback for debugging
        import traceback
        traceback.print_exc()

# Optional: Run standalone
if __name__ == "__main__":
    embed_parsed_functions()
