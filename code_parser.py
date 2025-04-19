import os
import ast
import json

def safe_read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Could not read {file_path}: {e}")
            return None

def extract_functions_from_file(file_path):
    source = safe_read_file(file_path)
    if source is None:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ SyntaxError in {file_path}: {e}")
        return []

    lines = source.splitlines()
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            name = node.name
            args = [arg.arg for arg in node.args.args]
            docstring = ast.get_docstring(node)

            start_line = node.lineno - 1
            end_line = getattr(node, 'end_lineno', start_line + 20)
            function_code = "\n".join(lines[start_line:end_line])

            functions.append({
                'file': file_path,
                'function_name': name,
                'args': args,
                'docstring': docstring,
                'code': function_code
            })

    return functions

def parse_python_files_in_directory(directory):
    print(f"🚀 Extracting functions...")
    all_functions = []
    
    for root, dirs, files in os.walk(directory):
        # Skip macOS system directories
        if "__MACOSX" in root:
            continue
            
        for file in files:
            # Skip macOS metadata files and non-python files
            if file.startswith("._") or not file.endswith(".py"):
                continue
                
            path = os.path.join(root, file)
            print(f"\n📄 Parsing: {path}")
            try:
                functions = extract_functions_from_file(path)
                all_functions.extend(functions)
            except ValueError as e:
                print(f"⚠️ Error parsing {path}: {e}")
                continue
            except Exception as e:
                print(f"⚠️ Unexpected error parsing {path}: {e}")
                continue
    
    return all_functions

def parse_codebase(directory):
    """
    Master function to call from main.py to parse and save functions.
    """
    if not os.path.isdir(directory):
        raise ValueError("❌ Invalid directory path.")

    print("🚀 Extracting functions...\n")
    functions = parse_python_files_in_directory(directory)
    print(f"\n✅ Extraction complete. {len(functions)} functions found.")

    with open("parsed_functions.json", 'w', encoding='utf-8') as f:
        json.dump(functions, f, indent=2)

    print("📦 Functions saved to parsed_functions.json")
