from code_search import load_all, find_top_functions
import ollama

# 🔄 Chat loop for CLI use (optional)
def ask_question_loop():
    model, index, metadata, function_data = load_all()
    print("\n🤖 You can now ask questions about your codebase! Type 'exit' to quit.\n")

    while True:
        question = input("❓ Ask your code question: ")
        if question.lower() in {"exit", "quit"}:
            print("👋 Exiting chat.")
            break

        print(generate_response(question, model, index, function_data))

# ✅ Web entrypoint — 1 question at a time
def ask_single_question(question):
    model, index, metadata, function_data = load_all()
    return generate_response(question, model, index, function_data)

# 🔧 Core logic shared by both functions above
def generate_response(question, model, index, function_data, k=3):
    try:
        top_function_indices = find_top_functions(question, model, index, function_data, k)
        code_blocks = ""

        for rank, idx in enumerate(top_function_indices):
            func = function_data[idx]
            code_blocks += f"\n#{rank+1} — From {func['file']}:\n```python\n{func['code']}\n```\n"

        prompt = f"""
        You are an AI assistant helping a junior developer understand a codebase.

        The user asked:
        \"{question}\"

        Here are the top {k} most relevant functions in the codebase:

        {code_blocks}

        Based on the most relevant function(s) below, answer the user's question directly and only refer to the relevant code.
        """

        response = ollama.chat(
            model='llama3.2:latest',
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains Python code clearly."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['message']['content']

    except Exception as e:
        return f"❌ Error generating response: {e}"

# ✅ Run standalone (CLI usage)
if __name__ == "__main__":
    ask_question_loop()
