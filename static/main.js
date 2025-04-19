document.addEventListener('DOMContentLoaded', () => {
  const networkContainer = document.getElementById('network');
  const chatBox = document.getElementById('chat-box');
  const chatForm = document.getElementById('chat-form');
  const input = document.getElementById('question');

  // Build diagram
  fetch('/diagram-data')
    .then(r => r.json())
    .then(buildDiagram)
    .catch(err => console.error(err));

  /* --------------  NEW buildDiagram  -------------- */
  function buildDiagram(modules) {
    const nodeData = {}; // id → full function object
    const nodes = [],
      edges = [];

    modules.forEach(m => {
      m.functions.forEach(f => {
        const id = f.qualified_name;
        nodeData[id] = f;

        nodes.push({
          id,
          label: f.name,
          shape: 'box',
          title: `<b>${id}</b>`, // tooltip on hover
          color: {
            background: '#fff',
            border: '#495057',
            highlight: { background: '#e7f1ff', border: '#0d6efd' },
          },
        });

        (f.calls || []).forEach(c => {
          const target = nodes.find(n => n.id === c)
            ? c
            : c.includes('.')
            ? c
            : `${m.name}.${c}`;
          edges.push({
            from: id,
            to: target,
            arrows: 'to',
            color: { color: '#e63900' },
            width: 3,
            smooth: { enabled: true, type: 'dynamic' },
          });
        });
      });
    });

    const network = new vis.Network(
      document.getElementById('network'),
      { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
      {
        layout: { improvedLayout: true },
        physics: { barnesHut: { springLength: 160 } },
        interaction: { hover: true },
      }
    );

    /* ---- on click: fill the details pane ---- */
    network.on('click', params => {
      if (!params.nodes.length) return;
      const id = params.nodes[0];
      const f = nodeData[id];
      if (!f) return;

      const pane = document.getElementById('details-pane');
      pane.classList.remove('hidden');
      document.getElementById('d-name').textContent = id;
      document.getElementById(
        'd-loc'
      ).textContent = `${f.module} (line ${f.line_number})`;
      document.getElementById('d-params').textContent =
        f.params && f.params.length ? f.params.join(', ') : 'None';
      document.getElementById('d-doc').textContent = f.docstring
        ? f.docstring
        : '—';

      // populate call list
      const ul = document.getElementById('d-calls');
      ul.innerHTML = '';
      (f.calls || []).forEach(c => {
        const li = document.createElement('li');
        li.textContent = c;
        ul.appendChild(li);
      });
    });
  }

  // Chat
  chatForm.addEventListener('submit', e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    addMsg('user', q);
    input.value = '';
    fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })
      .then(r => r.json())
      .then(d => addMsg('bot', d.answer))
      .catch(err => addMsg('bot', '❌ ' + err));
  });

  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = role;
    div.textContent = (role === 'user' ? '> ' : '') + text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
});
