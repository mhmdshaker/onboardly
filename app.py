import os
import zipfile
import shutil
import json

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from code_parser import parse_codebase
from embed_functions import embed_parsed_functions
from ask_question import ask_single_question
from function_mapper import ModuleAnalyzer

UPLOAD_FOLDER   = 'uploads'
EXTRACT_FOLDER  = 'workspace_code'
MODULES_JSON    = 'modules_data.json'

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def build_modules_json(code_dir):
    analyzer = ModuleAnalyzer()
    analyzer.analyze_directory(code_dir, recursive=True)

    modules_data = []
    for module_name, info in analyzer.modules.items():
        modules_data.append({
            'name': module_name,
            'path': info['path'],
            'functions': [
                { **({'calls': list(f['calls'])} if 'calls' in f else {}),
                  **{k:v for k,v in f.items() if k!='calls'} }
                for f in info['functions'].values()
            ]
        })

    with open(MODULES_JSON, 'w', encoding='utf-8') as fp:
        json.dump(modules_data, fp, indent=2)
    return MODULES_JSON

@app.route('/')
def welcome():
    return render_template('landing.html')

@app.route('/home')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('zipfile')
    if not file or not file.filename.endswith('.zip'):
        return 'Please upload a ZIP file.', 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(zip_path)

    # clean workspace
    if os.path.exists(EXTRACT_FOLDER):
        shutil.rmtree(EXTRACT_FOLDER)
    os.makedirs(EXTRACT_FOLDER)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(EXTRACT_FOLDER)

    # parse, embed, build modules JSON
    parse_codebase(EXTRACT_FOLDER)
    embed_parsed_functions()
    build_modules_json(EXTRACT_FOLDER)

    session['history'] = []
    # now send users to the Walkthrough page
    return redirect(url_for('walkthrough'))

@app.route('/walkthrough')
def walkthrough():
    return render_template('walkthrough.html')

@app.route('/diagram')
def diagram():
    return render_template('diagram.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/diagram-data')
def diagram_data():
    with open(MODULES_JSON, encoding='utf-8') as fp:
        return jsonify(json.load(fp))

@app.route('/chat', methods=['POST'])
def chat():
    q = request.json.get('question', '')
    answer = ask_single_question(q)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
