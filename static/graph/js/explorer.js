/**
 * explorer.js — Graphe D3.js force-directed pour l'explorateur relationnel
 */
(function() {
    'use strict';

    const CONFIG = window.GRAPH_CONFIG || {};
    const API_BASE = CONFIG.apiBase || '/api/v1/';
    const CSRF = CONFIG.csrfToken || '';

    const container = document.getElementById('graphContainer');
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    // SVG setup
    const svg = d3.select('#graphContainer')
        .append('svg')
        .attr('width', '100%')
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height]);

    // Zoom behavior
    const g = svg.append('g');
    const zoom = d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Arrowhead marker
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#999');

    // Layers
    const linkGroup = g.append('g').attr('class', 'links');
    const nodeGroup = g.append('g').attr('class', 'nodes');
    const labelGroup = g.append('g').attr('class', 'labels');

    // Force simulation
    const simulation = d3.forceSimulation()
        .force('link', d3.forceLink().id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30))
        .on('tick', ticked);

    let nodes = [];
    let links = [];

    function ticked() {
        linkGroup.selectAll('line')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        nodeGroup.selectAll('.node')
            .attr('transform', d => `translate(${d.x},${d.y})`);

        labelGroup.selectAll('text')
            .attr('x', d => d.x)
            .attr('y', d => d.y + 25);
    }

    function render() {
        // Links
        const link = linkGroup.selectAll('line')
            .data(links, d => d.id);
        link.exit().remove();
        link.enter().append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.max(1, d.poids || 1))
            .attr('marker-end', 'url(#arrowhead)')
            .append('title')
            .text(d => d.verbe || d.type_nom);

        // Nodes
        const node = nodeGroup.selectAll('.node')
            .data(nodes, d => d.id);
        node.exit().remove();
        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            .on('click', (event, d) => showDetail(d))
            .on('dblclick', (event, d) => expandNode(d));

        // Circle
        nodeEnter.append('circle')
            .attr('r', 16)
            .attr('fill', d => d.couleur || '#6366f1')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);

        // Anomaly halo
        nodeEnter.filter(d => d.has_anomalies)
            .insert('circle', 'circle')
            .attr('r', 22)
            .attr('fill', 'none')
            .attr('stroke', '#ef4444')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '4 2')
            .attr('class', 'anomaly-halo');

        // Icon text (using Unicode fallback)
        nodeEnter.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('fill', '#fff')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .text(d => (d.nom || '?')[0].toUpperCase());

        // Labels
        const label = labelGroup.selectAll('text')
            .data(nodes, d => d.id);
        label.exit().remove();
        label.enter().append('text')
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .attr('fill', '#666')
            .text(d => d.nom.length > 20 ? d.nom.substring(0, 18) + '...' : d.nom);

        // Update simulation
        simulation.nodes(nodes);
        simulation.force('link').links(links);
        simulation.alpha(0.5).restart();
    }

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    // Load graph from API
    function loadGraph(entiteId, profondeur) {
        profondeur = profondeur || document.getElementById('profondeur').value || 2;
        const url = `${API_BASE}graph-entites/${entiteId}/explore/?profondeur=${profondeur}`;

        fetch(url, {
            headers: { 'X-CSRFToken': CSRF },
            credentials: 'same-origin',
        })
        .then(r => r.json())
        .then(data => {
            nodes = data.nodes || [];
            links = data.links || [];
            render();
        })
        .catch(err => console.error('Graph load error:', err));
    }

    function expandNode(d) {
        const profondeur = 1;
        const url = `${API_BASE}graph-entites/${d.id}/explore/?profondeur=${profondeur}`;

        fetch(url, {
            headers: { 'X-CSRFToken': CSRF },
            credentials: 'same-origin',
        })
        .then(r => r.json())
        .then(data => {
            const existingIds = new Set(nodes.map(n => n.id));
            const newNodes = (data.nodes || []).filter(n => !existingIds.has(n.id));
            const existingLinkIds = new Set(links.map(l => l.id));
            const newLinks = (data.links || []).filter(l => !existingLinkIds.has(l.id));

            nodes = [...nodes, ...newNodes];
            links = [...links, ...newLinks];
            render();
        })
        .catch(err => console.error('Expand error:', err));
    }

    function showDetail(d) {
        const panel = document.getElementById('detailPanel');
        const title = document.getElementById('detailTitle');
        const content = document.getElementById('detailContent');
        panel.style.display = 'block';
        title.textContent = d.nom;

        const url = `${API_BASE}graph-entites/${d.id}/`;
        fetch(url, {
            headers: { 'X-CSRFToken': CSRF },
            credentials: 'same-origin',
        })
        .then(r => r.json())
        .then(detail => {
            let html = `
                <div class="mb-2">
                    <span class="badge" style="background:${detail.couleur}20;color:${detail.couleur}">
                        ${detail.type_nom}
                    </span>
                </div>
                ${detail.description ? `<p class="f-s-13">${detail.description}</p>` : ''}
            `;

            if (detail.attributs && Object.keys(detail.attributs).length) {
                html += '<h6 class="mt-2 f-s-13">Attributs</h6><table class="table table-sm">';
                for (const [k, v] of Object.entries(detail.attributs)) {
                    html += `<tr><td class="text-muted">${k}</td><td>${v}</td></tr>`;
                }
                html += '</table>';
            }

            html += `
                <div class="mt-3">
                    <a href="/graph/entites/${d.id}/" class="btn btn-sm btn-outline-primary me-1">
                        <i class="ph ph-eye me-1"></i>Détails
                    </a>
                    <a href="/graph/relations/creer/?source=${d.id}" class="btn btn-sm btn-outline-secondary">
                        <i class="ph ph-plus me-1"></i>Relation
                    </a>
                </div>
            `;
            content.innerHTML = html;
        });
    }

    // Close detail panel
    document.getElementById('closeDetail')?.addEventListener('click', () => {
        document.getElementById('detailPanel').style.display = 'none';
    });

    // Search entité
    const searchInput = document.getElementById('searchEntite');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const q = this.value.trim();
            if (q.length < 2) {
                document.getElementById('searchResults').style.display = 'none';
                return;
            }
            searchTimeout = setTimeout(() => {
                fetch(`${API_BASE}graph-entites/?search=${encodeURIComponent(q)}&page_size=10`, {
                    credentials: 'same-origin',
                })
                .then(r => r.json())
                .then(data => {
                    const results = data.results || [];
                    const dropdown = document.getElementById('searchResults');
                    if (!results.length) {
                        dropdown.style.display = 'none';
                        return;
                    }
                    dropdown.innerHTML = results.map(r => `
                        <a class="dropdown-item" href="#" data-id="${r.id}">
                            <i class="ph ${r.icone} me-2" style="color:${r.couleur}"></i>${r.nom}
                            <small class="text-muted ms-1">(${r.type_nom})</small>
                        </a>
                    `).join('');
                    dropdown.style.display = 'block';

                    dropdown.querySelectorAll('.dropdown-item').forEach(item => {
                        item.addEventListener('click', (e) => {
                            e.preventDefault();
                            const id = item.dataset.id;
                            dropdown.style.display = 'none';
                            searchInput.value = item.textContent.trim();
                            loadGraph(id);
                        });
                    });
                });
            }, 300);
        });
    }

    // Profondeur change
    document.getElementById('profondeur')?.addEventListener('change', function() {
        // If we have a current center node, reload
        if (nodes.length > 0) {
            const centerId = nodes[0]?.id;
            if (centerId) loadGraph(centerId, this.value);
        }
    });

    // Check URL params for initial load
    const urlParams = new URLSearchParams(window.location.search);
    const initialEntite = urlParams.get('entite');
    if (initialEntite) {
        loadGraph(initialEntite);
    }

    // Expose for external use
    window.GraphExplorer = { loadGraph, expandNode };
})();
