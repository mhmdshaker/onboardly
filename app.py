
import os, zipfile, shutil, json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from code_parser import parse_codebase
from embed_functions import embed_parsed_functions
from ask_question import ask_single_question
from function_mapper import ModuleAnalyzer

UPLOAD_FOLDER = 'uploads'
EXTRACT_FOLDER = 'workspace_code'

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------- helpers ----------
def build_modules_json(code_dir, outfile='modules_data.json'):
    analyzer = ModuleAnalyzer()
    analyzer.analyze_directory(code_dir, recursive=True)

    modules_data = []
    for module_name, info in analyzer.modules.items():
        module_entry = {
            'name': module_name,
            'path': info['path'],
            'functions': []
        }
        for func_name, f in info['functions'].items():
            func_clean = {k: (list(v) if isinstance(v, set) else v) for k, v in f.items()}
            module_entry['functions'].append(func_clean)
        modules_data.append(module_entry)

    with open(outfile, 'w', encoding='utf-8') as fp:
        json.dump(modules_data, fp, indent=2)
    return outfile

# ---------- routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('zipfile')
    if not file or not file.filename.endswith('.zip'):
        return 'Please upload a ZIP.', 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(zip_path)

    # fresh workspace
    if os.path.exists(EXTRACT_FOLDER):
        shutil.rmtree(EXTRACT_FOLDER)
    os.makedirs(EXTRACT_FOLDER)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(EXTRACT_FOLDER)

    # parse → embed → diagram data
    parse_codebase(EXTRACT_FOLDER)
    embed_parsed_functions()
    build_modules_json(EXTRACT_FOLDER)

    session['history'] = []
    return redirect(url_for('workspace'))

@app.route('/workspace')
def workspace():
    return render_template('workspace.html')

@app.route('/diagram-data')
def diagram_data():
    with open('modules_data.json', encoding='utf-8') as fp:
        return jsonify(json.load(fp))

@app.route('/chat', methods=['POST'])
def chat():
    q = request.json.get('question', '')
    answer = ask_single_question(q)
    # keep history server‑side if you need
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
