document.addEventListener('DOMContentLoaded', () => {
  const networkEl = document.getElementById('network');
  if (networkEl) {
    fetch('/diagram-data')
      .then(r => r.json())
      .then(buildDiagram)
      .catch(err => console.error('Error fetching diagram data:', err));
  }

  function buildDiagram(modules) {
    const nodeData = {};
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
      networkEl,
      { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
      {
        layout: { improvedLayout: true },
        physics: { barnesHut: { springLength: 160 } },
        interaction: { hover: true },
      }
    );

    // grab once
    const detailsPane = document.getElementById('details-pane');

    // clicking outside hides
    document.addEventListener('click', () =>
      detailsPane.classList.add('hidden')
    );

    // clicking on nodes
    network.on('click', params => {
      params.event.stopPropagation();
      if (!params.nodes.length) return;
      const id = params.nodes[0],
        f = nodeData[id];
      if (!f) return;

      // position pane
      const pos = network.canvasToDOM(network.getPositions([id])[id]);
      detailsPane.style.left = `${pos.x + 20}px`;
      detailsPane.style.top = `${pos.y - 20}px`;

      // fill content
      document.getElementById('d-name').textContent = id;
      document.getElementById(
        'd-loc'
      ).textContent = `${f.module} (line ${f.line_number})`;
      document.getElementById('d-params').textContent =
        (f.params || []).join(', ') || 'None';
      const docEl = document.getElementById('d-doc');
      if (f.docstring) {
        docEl.innerHTML = `<strong>Description:</strong> ${f.docstring}`;
      } else {
        docEl.textContent = 'No description available';
      }

      // calls list
      const ul = document.getElementById('d-calls');
      ul.innerHTML = '';
      (f.calls || []).forEach(c => {
        const li = document.createElement('li');
        li.textContent = c;
        ul.appendChild(li);
      });

      detailsPane.classList.remove('hidden');
    });
  }

  // Chat functionality
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    const input =
      document.getElementById('question') ||
      document.getElementById('chat-input');
    const chatBox = document.getElementById('chat-box');

    // Define the addMsg function in this scope so it can be used by the event handler
    function addMsg(role, text) {
      const div = document.createElement('div');
      div.className = role;
      div.textContent = (role === 'user' ? '> ' : '') + text;
      chatBox.appendChild(div);
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    chatForm.addEventListener('submit', e => {
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;

      addMsg('user', q);
      addMsg('bot', '⏳ Thinking...'); // Add loading indicator

      input.value = '';
      fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })
        .then(r => {
          if (!r.ok) throw new Error(`Server error: ${r.status}`);
          return r.json();
        })
        .then(d => {
          // Remove the loading message
          chatBox.removeChild(chatBox.lastChild);

          if (!d || !d.answer) {
            throw new Error('No answer in response');
          }
          addMsg('bot', d.answer);
        })
        .catch(err => {
          console.error('Chat error:', err);
          // Remove the loading message if it exists
          if (
            chatBox.lastChild &&
            chatBox.lastChild.textContent.includes('⏳')
          ) {
            chatBox.removeChild(chatBox.lastChild);
          }
          addMsg('bot', `❌ Error: ${err.message}`);
        });
    });
  }
});
