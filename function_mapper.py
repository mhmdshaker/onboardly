import ast
import os
import argparse
import json
from typing import Dict, List, Set, Optional, Tuple


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor that extracts function definitions and their calls."""
    
    def __init__(self):
        self.functions = {}  # name -> FunctionInfo
        self.current_function = None
        self.current_class = None
        
    def visit_ClassDef(self, node):
        """Process a class definition."""
        prev_class = self.current_class
        self.current_class = node.name
        
        # Visit all contents of the class
        self.generic_visit(node)
        
        # Restore previous context
        self.current_class = prev_class
        
    def visit_FunctionDef(self, node):
        """Process a function definition."""
        function_name = node.name
        
        # If we're in a class, prefix with class name
        if self.current_class:
            qualified_name = f"{self.current_class}.{function_name}"
        else:
            qualified_name = function_name
            
        params = [arg.arg for arg in node.args.args if arg.arg != 'self']
        doc_string = ast.get_docstring(node)
        
        # Get function source code
        source_lines = []
        for i in range(node.lineno, node.end_lineno + 1):
            source_lines.append(self.source_lines[i-1])
        function_source = ''.join(source_lines)
        
        # Save the current function to restore after processing this one
        parent_function = self.current_function
        self.current_function = qualified_name
        
        # Create function info
        self.functions[qualified_name] = {
            'name': function_name,
            'qualified_name': qualified_name,
            'class': self.current_class,
            'params': params,
            'docstring': doc_string,
            'calls': set(),
            'line_number': node.lineno,
            'end_line': node.end_lineno,
            'parent': parent_function,
            'source': function_source
        }
        
        # Visit the function body to find calls
        self.generic_visit(node)
        
        # Restore parent function context
        self.current_function = parent_function
        
    def visit_Call(self, node):
        """Process a function call."""
        if self.current_function:
            if isinstance(node.func, ast.Name):
                # Direct function call
                self.functions.setdefault(self.current_function, {}).setdefault('calls', set()).add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Method call or attribute access
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'self' and self.current_class:
                        # Self method call within class
                        self.functions.setdefault(self.current_function, {}).setdefault('calls', set()).add(f"{self.current_class}.{node.func.attr}")
                    else:
                        # Other attribute call
                        self.functions.setdefault(self.current_function, {}).setdefault('calls', set()).add(f"{node.func.value.id}.{node.func.attr}")
                else:
                    # Generic method call
                    self.functions.setdefault(self.current_function, {}).setdefault('calls', set()).add(node.func.attr)
        
        # Continue visiting children
        self.generic_visit(node)
    
    def set_source(self, source_lines):
        """Set the source code lines for reference."""
        self.source_lines = source_lines


class ModuleAnalyzer:
    """Analyze Python modules for function definitions and relationships."""
    
    def __init__(self):
        self.modules = {}
        
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                code = file.read()
                source_lines = code.splitlines(True)  # Keep line endings
                tree = ast.parse(code)
                
                visitor = FunctionVisitor()
                visitor.set_source(source_lines)
                visitor.visit(tree)
                
                module_name = os.path.basename(file_path).replace('.py', '')
                self.modules[module_name] = {
                    'path': file_path,
                    'functions': visitor.functions
                }
                
                return visitor.functions
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                return {}
    
    def analyze_directory(self, directory: str, recursive: bool = True) -> None:
        """Analyze all Python files in a directory."""
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.analyze_file(file_path)
                    
            if not recursive:
                break

    def generate_interactive_html(self, output_file: str = 'function_map.html'):
        """Generate an interactive HTML visualization."""
        # Prepare data structure for visualization
        modules_data = []
        
        for module_name, module_info in self.modules.items():
            module_data = {
                'name': module_name,
                'path': module_info['path'],
                'functions': []
            }
            
            for func_name, func_info in module_info['functions'].items():
                # Convert sets to lists for JSON serialization
                func_data = {k: v if not isinstance(v, set) else list(v) for k, v in func_info.items()}
                module_data['functions'].append(func_data)
            
            modules_data.append(module_data)
        
        # Generate HTML template
        html_content = self._generate_html_template(modules_data)
        
        # Write HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Interactive visualization saved to {output_file}")
        
    def _generate_html_template(self, data):
        """Generate the HTML template with embedded JSON data."""
        js_data = json.dumps(data)
        
        html = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Interactive Function Map</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                background-color: #f5f5f5;
            }}
            
            .sidebar {{
                width: 300px;
                background-color: #f8f9fa;
                height: 100vh;
                overflow-y: auto;
                border-right: 1px solid #dee2e6;
                padding: 15px;
            }}
            
            .main-content {{
                flex-grow: 1;
                height: 100vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}
            
            .function-list {{
                list-style-type: none;
                padding: 0;
                margin: 0;
            }}
            
            .function-list li {{
                padding: 8px 10px;
                cursor: pointer;
                border-radius: 4px;
                margin-bottom: 2px;
            }}
            
            .function-list li:hover {{
                background-color: #e9ecef;
            }}
            
            .function-list li.active {{
                background-color: #d0e8ff;
            }}
            
            .module-header {{
                font-weight: bold;
                margin-top: 15px;
                margin-bottom: 5px;
                color: #495057;
            }}
            
            .visualization-area {{
                flex-grow: 1;
                overflow: hidden;
                position: relative;
                background-color: #ffffff;
            }}
            
            .details-area {{
                height: 40%;
                overflow-y: auto;
                padding: 15px;
                border-top: 1px solid #dee2e6;
                background-color: #f8f9fa;
            }}
            
            .function-node {{
                position: absolute;
                background-color: #fff;
                border: 2px solid #6c757d;
                border-radius: 8px;
                padding: 10px;
                min-width: 150px;
                max-width: 250px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: box-shadow 0.3s;
                cursor: pointer;
                overflow: hidden;
                transform-origin: 0 0;
            }}
            
            .function-node:hover {{
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
            }}
            
            .function-node.selected {{
                border-color: #0d6efd;
                background-color: #e7f1ff;
            }}
            
            .function-node h3 {{
                margin: 0 0 5px 0;
                font-size: 14px;
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }}
            
            .function-node p {{
                margin: 0;
                font-size: 12px;
                color: #6c757d;
            }}
            
            .connector {{
                position: absolute;
                pointer-events: none;
            }}
            
            .connector path {{
                stroke: red !important;
                stroke-width: 5px !important;
                fill: none !important;
            }}
            
            
            .search-box {{
                margin-bottom: 15px;
                width: 100%;
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }}
            
            .details-header {{
                margin-top: 0;
                color: #212529;
            }}
            
            .details-section {{
                margin-bottom: 15px;
            }}
            
            .details-label {{
                font-weight: bold;
                color: #495057;
                margin-bottom: 5px;
            }}
            
            .source-code {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                white-space: pre-wrap;
                overflow-x: auto;
            }}
            
            .call-list {{
                list-style-type: none;
                padding: 0;
            }}
            
            .call-list li {{
                padding: 3px 0;
                cursor: pointer;
                color: #0d6efd;
            }}
            
            .call-list li:hover {{
                text-decoration: underline;
            }}
            
            .toolbar {{
                padding: 10px;
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .toolbar button {{
                background-color: #fff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px 10px;
                cursor: pointer;
                margin-right: 5px;
            }}
            
            .toolbar button:hover {{
                background-color: #e9ecef;
            }}
            
            .zoom-controls {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                display: flex;
                flex-direction: column;
            }}
            
            .zoom-controls button {{
                background-color: #fff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                width: 36px;
                height: 36px;
                margin: 5px 0;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            
            .zoom-controls button:hover {{
                background-color: #e9ecef;
            }}
            
            #nodes {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }}
            
            #connections {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                transform-origin: 0 0;
                pointer-events: none;
                z-index: 0;
            }}

            .connector.highlighted path {{
                stroke: #0d6efd;
                stroke-width: 3;
            }}

            .connector .arrow {{
                fill: #adb5bd;
                transition: fill 0.3s;
            }}

            .connector.highlighted .arrow {{
                fill: #0d6efd;
            }}

        </style>
    </head>
    <body>
        <div class="sidebar">
            <input type="text" class="search-box" id="searchBox" placeholder="Search functions...">
            <div id="functionsList"></div>
        </div>
        
        <div class="main-content">
            <div class="toolbar">
                <div>
                    <button id="resetViewBtn">Reset View</button>
                    <button id="autoLayoutBtn">Auto Layout</button>
                    <button id="expandAllBtn">Expand All</button>
                </div>
                <div>
                    <span id="selectedFunction"></span>
                </div>
            </div>
            
            <div class="visualization-area" id="visualizationArea">
                <svg id="connections" width="100%" height="100%"></svg>
                <div id="nodes"></div>
                
                <div class="zoom-controls">
                    <button id="zoomInBtn">+</button>
                    <button id="zoomOutBtn">-</button>
                </div>
            </div>
            
            <div class="details-area" id="detailsArea">
                <h3 class="details-header">Select a function to view details</h3>
            </div>
        </div>

        <script>
            // Data from Python script
            const modulesData = {js_data};
            
            // Global variables
            let functions = {{}};
            let nodePositions = {{}};
            let selectedFunction = null;
            let draggedNode = null;
            let dragOffsetX = 0;
            let dragOffsetY = 0;
            let scale = 1;
            let translateX = 0;
            let translateY = 0;
            let isDraggingCanvas = false;
            let dragStartX = 0;
            let dragStartY = 0;
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {{
                console.log("Initializing function map visualization...");
                console.log("Modules data:", modulesData);
                
                initializeFunctions();
                initializeUI();
                renderFunctionList();
                detectEntryPoint();
            }});
            
            function initializeFunctions() {{
                console.log("Initializing functions...");
                // Process the data and create a flat functions object
                modulesData.forEach(module => {{
                    module.functions.forEach(func => {{
                        const qualifiedName = `${{module.name}}.${{func.qualified_name}}`;
                        functions[qualifiedName] = {{
                            ...func,
                            module: module.name,
                            modulePath: module.path,
                            // Convert calls to include module name if not explicitly included
                            calls: (func.calls || []).map(call => {{
                                if (call.includes('.')) {{
                                    return call;
                                }} else {{
                                    // Check if call exists in this module
                                    const inModule = module.functions.some(f => f.name === call);
                                    return inModule ? `${{module.name}}.${{call}}` : call;
                                }}
                            }})
                        }};
                    }});
                }});
                console.log("Functions initialized:", Object.keys(functions).length);
            }}
            
            function initializeUI() {{
                console.log("Initializing UI elements...");
                // Set up event listeners
                document.getElementById('searchBox').addEventListener('input', handleSearch);
                document.getElementById('resetViewBtn').addEventListener('click', resetView);
                document.getElementById('autoLayoutBtn').addEventListener('click', autoLayout);
                document.getElementById('expandAllBtn').addEventListener('click', expandAll);
                document.getElementById('zoomInBtn').addEventListener('click', () => zoom(1.2));
                document.getElementById('zoomOutBtn').addEventListener('click', () => zoom(0.8));
                
                // Set up drag events for canvas
                const visualizationArea = document.getElementById('visualizationArea');
                visualizationArea.addEventListener('mousedown', startDragCanvas);
                visualizationArea.addEventListener('mousemove', dragCanvas);
                visualizationArea.addEventListener('mouseup', endDragCanvas);
                visualizationArea.addEventListener('mouseleave', endDragCanvas);
                
                // Zoom with mouse wheel
                visualizationArea.addEventListener('wheel', handleWheel);
            }}
            
            function renderFunctionList() {{
                console.log("Rendering function list...");
                const listContainer = document.getElementById('functionsList');
                listContainer.innerHTML = '';
                
                // Group by module
                const moduleGroups = {{}};
                
                Object.values(functions).forEach(func => {{
                    if (!moduleGroups[func.module]) {{
                        moduleGroups[func.module] = [];
                    }}
                    moduleGroups[func.module].push(func);
                }});
                
                // Create module sections
                Object.entries(moduleGroups).forEach(([moduleName, moduleFunctions]) => {{
                    const moduleHeader = document.createElement('div');
                    moduleHeader.className = 'module-header';
                    moduleHeader.textContent = moduleName;
                    listContainer.appendChild(moduleHeader);
                    
                    const moduleList = document.createElement('ul');
                    moduleList.className = 'function-list';
                    
                    // Sort functions by line number
                    moduleFunctions.sort((a, b) => a.line_number - b.line_number);
                    
                    moduleFunctions.forEach(func => {{
                        const item = document.createElement('li');
                        item.textContent = func.name;
                        item.dataset.id = `${{func.module}}.${{func.qualified_name}}`;
                        item.addEventListener('click', () => selectFunction(item.dataset.id));
                        moduleList.appendChild(item);
                    }});
                    
                    listContainer.appendChild(moduleList);
                }});
            }}
            
            function handleSearch(e) {{
                const searchTerm = e.target.value.toLowerCase();
                const items = document.querySelectorAll('.function-list li');
                
                items.forEach(item => {{
                    const funcName = item.textContent.toLowerCase();
                    const funcId = item.dataset.id.toLowerCase();
                    const visible = funcName.includes(searchTerm) || funcId.includes(searchTerm);
                    item.style.display = visible ? 'block' : 'none';
                }});
            }}
            
            function detectEntryPoint() {{
                console.log("Detecting entry point...");
                // Look for main function
                const mainFunction = Object.keys(functions).find(key => key.endsWith('.main'));
                
                if (mainFunction) {{
                    console.log("Found main function:", mainFunction);
                    selectFunction(mainFunction);
                    return;
                }}
                
                // If no main function, select first function
                const firstFunction = Object.keys(functions)[0];
                if (firstFunction) {{
                    console.log("No main function found. Using first function:", firstFunction);
                    selectFunction(firstFunction);
                }}
            }}
            
            function selectFunction(funcId, centerView = true) {{
                console.log("Selecting function:", funcId);
                // Update selected function
                selectedFunction = funcId;
                
                // Update UI to show selection
                document.querySelectorAll('.function-list li').forEach(item => {{
                    item.classList.toggle('active', item.dataset.id === funcId);
                }});
                
                // Update selected function indicator
                document.getElementById('selectedFunction').textContent = funcId;
                
                // Render visualization
                renderVisualization(funcId, centerView);
                
                // Show function details
                showFunctionDetails(funcId);
            }}
            
            function renderVisualization(funcId, centerView = true) {{
                console.log("Rendering visualization for:", funcId);
                const nodesContainer = document.getElementById('nodes');
                const connectionsContainer = document.getElementById('connections');
                
                // Clear existing nodes and connections
                nodesContainer.innerHTML = '';
                connectionsContainer.innerHTML = '';
                
                if (!funcId || !functions[funcId]) {{
                    console.warn("Function not found:", funcId);
                    return;
                }}
                
                // Build the visualization graph
                const visited = new Set();
                const toVisit = [funcId];
                const graph = {{}};
                
                // Breadth-first traversal to build graph
                while (toVisit.length > 0) {{
                    const currentId = toVisit.shift();
                    
                    if (visited.has(currentId)) {{
                        continue;
                    }}
                    
                    visited.add(currentId);
                    
                    const func = functions[currentId];
                    if (!func) {{
                        continue; // Function not found
                    }}
                    
                    graph[currentId] = {{
                        func,
                        children: []
                    }};
                    
                    // Add calls
                    if (func.calls) {{
                        func.calls.forEach(call => {{
                            // Check if this call exists in our functions
                            if (functions[call]) {{
                                graph[currentId].children.push(call);
                                if (!visited.has(call)) {{
                                    toVisit.push(call);
                                }}
                            }}
                        }});
                    }}
                }}
                
                console.log("Built graph with", Object.keys(graph).length, "nodes");
                
                // Position nodes if not already positioned
                if (centerView || Object.keys(nodePositions).length === 0) {{
                    autoLayoutGraph(graph, funcId);
                }}
                
                // Create nodes
                Object.keys(graph).forEach(id => {{
                    createFunctionNode(id, graph[id].func);
                }});
                
                // Create connections
                Object.entries(graph).forEach(([fromId, nodeData]) => {{
                    nodeData.children.forEach(toId => {{
                        if (graph[toId]) {{
                            createConnection(fromId, toId);
                            console.log("Creating connection from", fromId, "to", toId);
                        }}
                    }});
                }});
                
                // Apply transform to nodes container
                applyTransform();
            }}
            
            function autoLayoutGraph(graph, rootId) {{
                console.log("Auto-layouting graph from root:", rootId);
                // Simple layer-based layout
                const layers = {{}};
                const visited = new Set();
                
                function assignLayer(id, layer) {{
                    if (visited.has(id)) {{
                        return;
                    }}
                    
                    visited.add(id);
                    
                    if (!layers[layer]) {{
                        layers[layer] = [];
                    }}
                    
                    layers[layer].push(id);
                    
                    const node = graph[id];
                    if (node && node.children) {{
                        node.children.forEach(childId => {{
                            if (graph[childId]) {{
                                assignLayer(childId, layer + 1);
                            }}
                        }});
                    }}
                }}
                
                // Start with root node
                assignLayer(rootId, 0);
                
                console.log("Created", Object.keys(layers).length, "layers");
                
                // Position nodes by layer
                const layerHeight = 180;
                const nodeWidth = 200;
                const nodeMargin = 30;
                
                Object.keys(layers).forEach(layer => {{
                    const nodesInLayer = layers[layer];
                    const layerWidth = nodesInLayer.length * (nodeWidth + nodeMargin);
                    const startX = -layerWidth / 2 + nodeWidth / 2;
                    
                    nodesInLayer.forEach((id, index) => {{
                        nodePositions[id] = {{
                            x: startX + index * (nodeWidth + nodeMargin),
                            y: parseInt(layer) * layerHeight
                        }};
                    }});
                }});
                
                // Center the view
                const visualizationArea = document.getElementById('visualizationArea');
                translateX = visualizationArea.clientWidth / 2;
                translateY = visualizationArea.clientHeight / 3;
                scale = 1;
                
                console.log("Node positions calculated:", Object.keys(nodePositions).length);
            }}
            
            function createFunctionNode(id, func) {{
                if (!nodePositions[id]) {{
                    // Default position if not set
                    const visualizationArea = document.getElementById('visualizationArea');
                    nodePositions[id] = {{
                        x: Math.random() * (visualizationArea.clientWidth - 200),
                        y: Math.random() * (visualizationArea.clientHeight - 100)
                    }};
                    console.log("Created default position for", id, nodePositions[id]);
                }}
                
                const node = document.createElement('div');
                node.className = 'function-node';
                node.id = `node-${{id.replace(/\\./g, '-')}}`;
                node.dataset.id = id;
                node.classList.toggle('selected', id === selectedFunction);
                
                node.innerHTML = `
                    <h3>${{func.name}}</h3>
                    <p>${{func.module}}</p>
                `;
                
                node.style.left = `${{nodePositions[id].x}}px`;
                node.style.top = `${{nodePositions[id].y}}px`;
                
                // Add event listeners
                node.addEventListener('mousedown', startDragNode);
                node.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    selectFunction(id, false);
                }});
                
                document.getElementById('nodes').appendChild(node);
                console.log("Created node:", id, "at", nodePositions[id].x, nodePositions[id].y);
            }}
            
            function createConnection(fromId, toId) {{
                const svgNS = "http://www.w3.org/2000/svg";
                const connectionId = `connection-${{fromId.replace(/\\./g, '-')}}-${{toId.replace(/\\./g, '-')}}`;
                
                if (document.getElementById(connectionId)) {{
                    // Just update it if it exists
                    updateConnection(fromId, toId);
                    return;
                }}

                const connGroup = document.createElementNS(svgNS, "g");
                connGroup.setAttribute("id", connectionId);
                connGroup.setAttribute("class", "connector");
                connGroup.setAttribute("data-from", fromId);
                connGroup.setAttribute("data-to", toId);
                
                const path = document.createElementNS(svgNS, "path");
                connGroup.appendChild(path);

                // Add arrow
                const arrow = document.createElementNS(svgNS, "path");
                arrow.setAttribute("class", "arrow");
                arrow.setAttribute("fill", "#adb5bd");
                connGroup.appendChild(arrow);
                
                document.getElementById('connections').appendChild(connGroup);
                
                updateConnection(fromId, toId);
                console.log("Created connection from", fromId, "to", toId);
            }}
            
            function updateConnection(fromId, toId) {{
                const connId = `connection-${{fromId.replace(/\./g, '-')}}-${{toId.replace(/\./g, '-')}}`;
                const conn = document.getElementById(connId);
                
                if (!conn) {{
                    console.warn("Connection not found:", connId);
                    return;
                }}
                
                // Get node elements
                const fromNodeId = `node-${{fromId.replace(/\./g, '-')}}`;
                const toNodeId = `node-${{toId.replace(/\./g, '-')}}`;
                const fromNode = document.getElementById(fromNodeId);
                const toNode = document.getElementById(toNodeId);

                if (!fromNode || !toNode) {{
                    console.warn("Nodes not found for connection", fromId, toId);
                    return;
                }}
                
                // Get node positions from nodePositions
                const fromPos = nodePositions[fromId];
                const toPos = nodePositions[toId];
                
                if (!fromPos || !toPos) {{
                    console.warn("Missing position data for connection", fromId, toId);
                    return;
                }}
                
                // Node dimensions (approximations)
                const nodeWidth = 180;
                const nodeHeight = 80;
                
                // Calculate center points
                const fromX = fromPos.x + nodeWidth / 2;
                const fromY = fromPos.y + nodeHeight / 2;
                const toX = toPos.x + nodeWidth / 2;
                const toY = toPos.y + nodeHeight / 2;
                
                // Calculate the angle between nodes
                const dx = toX - fromX;
                const dy = toY - fromY;
                const angle = Math.atan2(dy, dx);
                
                // Adjust start and end points to the edges of nodes
                const startX = fromX + Math.cos(angle) * (nodeWidth / 2);
                const startY = fromY + Math.sin(angle) * (nodeHeight / 2);
                const endX = toX - Math.cos(angle) * (nodeWidth / 2);
                const endY = toY - Math.sin(angle) * (nodeHeight / 2);
                
                // Create a curved path
                const distance = Math.sqrt(dx * dx + dy * dy);
                const curveStrength = Math.min(distance * 0.2, 50);
                const midX = (startX + endX) / 2;
                const midY = (startY + endY) / 2 - curveStrength;
                
                // Draw a quadratic curve
                const path = conn.querySelector('path');
                path.setAttribute("d", `M${{startX}},${{startY}} Q${{midX}},${{midY}} ${{endX}},${{endY}}`);
                
                // Add arrowhead
                const arrowSize = 10;
                const arrowAngle = Math.atan2(endY - midY, endX - midX);
                
                const arrowX1 = endX - arrowSize * Math.cos(arrowAngle - Math.PI/6);
                const arrowY1 = endY - arrowSize * Math.sin(arrowAngle - Math.PI/6);
                const arrowX2 = endX - arrowSize * Math.cos(arrowAngle + Math.PI/6);
                const arrowY2 = endY - arrowSize * Math.sin(arrowAngle + Math.PI/6);
                
                const arrowPath = `M${{endX}},${{endY}} L${{arrowX1}},${{arrowY1}} L${{arrowX2}},${{arrowY2}} Z`;
                
                const arrow = conn.querySelector('.arrow');
                if (arrow) {{
                    arrow.setAttribute("d", arrowPath);
                }}
            }}
            
            function updateAllConnections() {{
                // Get all connector elements
                const connectors = document.querySelectorAll('.connector');
                
                connectors.forEach(connector => {{
                    const fromId = connector.getAttribute('data-from');
                    const toId = connector.getAttribute('data-to');
                    
                    if (fromId && toId) {{
                        updateConnection(fromId, toId);
                    }}
                }});
            }}
            
            function showFunctionDetails(funcId) {{
                const detailsArea = document.getElementById('detailsArea');
                const func = functions[funcId];
                
                if (!func) {{
                    detailsArea.innerHTML = '<h3 class="details-header">Function not found</h3>';
                    return;
                }}
                
                // Format the source code with simple syntax highlighting
                let sourceCode = func.source || "Source code not available";
                
                // Build HTML
                let html = `
                    <h3 class="details-header">${{func.qualified_name}}</h3>
                    
                    <div class="details-section">
                        <div class="details-label">Location</div>
                        <div>${{func.module}} (line ${{func.line_number}})</div>
                    </div>
                    
                    <div class="details-section">
                        <div class="details-label">Parameters</div>
                        <div>${{func.params && func.params.length ? func.params.join(', ') : 'None'}}</div>
                    </div>
                `;
                
                if (func.docstring) {{
                    html += `
                        <div class="details-section">
                            <div class="details-label">Documentation</div>
                            <div>${{func.docstring.replace(/\\n/g, '<br>')}}</div>
                        </div>
                    `;
                }}
                
                // Function calls
                const calls = func.calls || [];
                html += `
                    <div class="details-section">
                        <div class="details-label">Calls</div>
                        <ul class="call-list">
                `;
                
                if (calls.length === 0) {{
                    html += '<li>None</li>';
                }} else {{
                    calls.forEach(call => {{
                        if (functions[call]) {{
                            html += `<li data-id="${{call}}" class="function-link">${{call}}</li>`;
                        }} else {{
                            html += `<li>${{call}} (external)</li>`;
                        }}
                    }});
                }}
                
                html += `
                        </ul>
                    </div>
                `;
                
                // Called by
                const calledBy = Object.values(functions).filter(f => 
                    (f.calls || []).includes(func.qualified_name) || 
                    (f.calls || []).includes(func.name)
                );
                
                html += `
                    <div class="details-section">
                        <div class="details-label">Called By</div>
                        <ul class="call-list">
                `;

                if (calledBy.length === 0) {{
                    html += '<li>None</li>';
                }} else {{
                    calledBy.forEach(caller => {{
                        const callerId = `${{caller.module}}.${{caller.qualified_name}}`;
                        html += `<li data-id="${{callerId}}" class="function-link">${{callerId}}</li>`;
                    }});
                }}
                
                html += `
                        </ul>
                    </div>
                `;
                
                // Source code
                html += `
                    <div class="details-section">
                        <div class="details-label">Source Code</div>
                        <pre class="source-code">${{sourceCode}}</pre>
                    </div>
                `;
                
                detailsArea.innerHTML = html;
                
                // Add event listeners to function links
                document.querySelectorAll('.function-link').forEach(link => {{
                    link.addEventListener('click', () => {{
                        selectFunction(link.dataset.id);
                    }});
                }});
            }}
            
            function startDragNode(e) {{
                e.stopPropagation();
                draggedNode = e.target.closest('.function-node');
                if (!draggedNode) return;
                
                const nodeId = draggedNode.dataset.id;
                console.log("Start dragging node:", nodeId);
                
                // Calculate drag offset in transformed coordinates
                dragOffsetX = e.clientX - (nodePositions[nodeId].x * scale + translateX);
                dragOffsetY = e.clientY - (nodePositions[nodeId].y * scale + translateY);
                
                document.addEventListener('mousemove', dragNode);
                document.addEventListener('mouseup', endDragNode);
            }}
            
            function dragNode(e) {{
                if (!draggedNode) return;
                
                const nodeId = draggedNode.dataset.id;
                
                // Calculate new position in transformed coordinates
                const newX = (e.clientX - dragOffsetX - translateX) / scale;
                const newY = (e.clientY - dragOffsetY - translateY) / scale;
                
                // Update node position data
                nodePositions[nodeId] = {{ x: newX, y: newY }};
                
                // Update node position visually
                draggedNode.style.left = `${{newX}}px`;
                draggedNode.style.top = `${{newY}}px`;
                
                // Update connections
                updateAllConnections();
            }}
            
            function endDragNode() {{
                if (draggedNode) {{
                    console.log("End dragging node:", draggedNode.dataset.id);
                }}
                draggedNode = null;
                document.removeEventListener('mousemove', dragNode);
                document.removeEventListener('mouseup', endDragNode);
            }}
            
            function startDragCanvas(e) {{
                // Ignore if clicking on a node
                if (e.target.closest('.function-node')) return;
                
                isDraggingCanvas = true;
                dragStartX = e.clientX;
                dragStartY = e.clientY;
                
                e.preventDefault();
                console.log("Start dragging canvas");
            }}
            
            function dragCanvas(e) {{
                if (!isDraggingCanvas) return;
                
                const dx = e.clientX - dragStartX;
                const dy = e.clientY - dragStartY;
                
                translateX += dx;
                translateY += dy;
                
                applyTransform();
                
                dragStartX = e.clientX;
                dragStartY = e.clientY;
            }}
            
            function endDragCanvas() {{
                isDraggingCanvas = false;
            }}
            
            function handleWheel(e) {{
                e.preventDefault();
                
                // Get mouse position relative to visualization area
                const visualizationArea = document.getElementById('visualizationArea');
                const rect = visualizationArea.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                // Zoom factor
                const factor = e.deltaY < 0 ? 1.1 : 0.9;
                
                // Adjust scale
                const newScale = scale * factor;
                
                // Limit scale to reasonable values
                if (newScale > 0.2 && newScale < 3) {{
                    // Calculate new translate values to zoom toward mouse position
                    translateX = mouseX - (mouseX - translateX) * factor;
                    translateY = mouseY - (mouseY - translateY) * factor;
                    scale = newScale;
                    
                    applyTransform();
                }}
            }}
            
            function zoom(factor) {{
                const visualizationArea = document.getElementById('visualizationArea');
                const centerX = visualizationArea.clientWidth / 2;
                const centerY = visualizationArea.clientHeight / 2;
                
                // Adjust scale
                const newScale = scale * factor;
                
                // Limit scale to reasonable values
                if (newScale > 0.2 && newScale < 3) {{
                    // Calculate new translate values to zoom toward center
                    translateX = centerX - (centerX - translateX) * factor;
                    translateY = centerY - (centerY - translateY) * factor;
                    scale = newScale;
                    
                    applyTransform();
                }}
            }}
            
            function applyTransform() {{
                const nodesContainer = document.getElementById('nodes');
                nodesContainer.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
                
                const connectionsContainer = document.getElementById('connections');
                connectionsContainer.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;

                updateAllConnections();
            }}
            
            function resetView() {{
                scale = 1;
                const visualizationArea = document.getElementById('visualizationArea');
                translateX = visualizationArea.clientWidth / 2;
                translateY = visualizationArea.clientHeight / 3;
                
                applyTransform();
            }}
            
            function autoLayout() {{
                // Clear existing positions
                nodePositions = {{}};
                
                // Re-render with the current selected function
                if (selectedFunction) {{
                    renderVisualization(selectedFunction, true);
                }}
            }}
            
            function expandAll() {{
                // Build a complete graph of all functions
                const rootFunction = selectedFunction || Object.keys(functions)[0];
                
                if (!rootFunction) return;
                
                // Clear existing positions
                nodePositions = {{}};
                
                // Build a graph of all functions
                const graph = {{}};
                
                Object.keys(functions).forEach(id => {{
                    graph[id] = {{
                        func: functions[id],
                        children: []
                    }};
                    
                    // Add calls
                    if (functions[id].calls) {{
                        functions[id].calls.forEach(call => {{
                            if (functions[call]) {{
                                graph[id].children.push(call);
                            }}
                        }});
                    }}
                }});
                
                // Position all nodes
                autoLayoutGraph(graph, rootFunction);
                
                // Render the full graph
                renderVisualization(rootFunction, true);
            }}
        </script>
    </body>
    </html>'''
        
        return html

def main():
    parser = argparse.ArgumentParser(description='Analyze Python code and visualize function relationships')
    parser.add_argument('target', help='Python file or directory to analyze')
    parser.add_argument('-o', '--output', default='function_map.html', help='Output HTML file')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursively analyze directories')
    
    args = parser.parse_args()
    
    analyzer = ModuleAnalyzer()
    
    if os.path.isfile(args.target) and args.target.endswith('.py'):
        analyzer.analyze_file(args.target)
    elif os.path.isdir(args.target):
        analyzer.analyze_directory(args.target, args.recursive)
    else:
        print(f"Error: {args.target} is not a Python file or directory")
        return 1
    
    analyzer.generate_interactive_html(args.output)
    return 0

if __name__ == "__main__":
    exit(main())