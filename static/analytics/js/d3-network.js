/**
 * Force-directed Network - Écosystème Clients
 * Réseau interactif clients ↔ mandats.
 */
(function() {
    'use strict';

    var container = document.getElementById('network-container');
    if (!container) return;

    var currentData = null;
    var simulation = null;

    var typeColors = {
        'client': AltiusD3.colors.primary,
        'mandat': AltiusD3.colors.success,
    };

    var mandatColors = {
        'COMPTA': '#3b82f6',
        'TVA': '#06b6d4',
        'SALAIRES': '#f59e0b',
        'FISCAL': '#8b5cf6',
        'REVISION': '#ec4899',
        'CONSEIL': '#10b981',
        'CREATION': '#f97316',
        'GLOBAL': '#6b7280',
    };

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        if (!data || !data.nodes || data.nodes.length === 0) {
            AltiusD3.showEmpty(container, 'ph ph-graph', 'Aucun client actif');
            return;
        }

        var width = container.clientWidth;
        var height = Math.max(400, container.clientHeight || 450);

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [0, 0, width, height].join(' '));

        // Zoom
        var g = svg.append('g');
        svg.call(d3.zoom()
            .scaleExtent([0.2, 5])
            .on('zoom', function(event) {
                g.attr('transform', event.transform);
            })
        );

        // Size scale for nodes
        var maxVal = d3.max(data.nodes, function(d) { return d.value; }) || 1;
        var sizeScale = d3.scaleSqrt().domain([0, maxVal]).range([6, 30]);

        // Simulation
        if (simulation) simulation.stop();
        simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links)
                .id(function(d) { return d.id; })
                .distance(100))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(function(d) {
                return sizeScale(d.value) + 5;
            }));

        // Links
        var link = g.append('g')
            .selectAll('.link')
            .data(data.links)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', function(d) {
                return mandatColors[d.type] || AltiusD3.colors.gray;
            })
            .attr('stroke-width', 1.5);

        // Nodes
        var node = g.append('g')
            .selectAll('.node')
            .data(data.nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragStarted)
                .on('drag', dragged)
                .on('end', dragEnded));

        node.append('circle')
            .attr('r', function(d) { return sizeScale(d.value); })
            .attr('fill', function(d) { return typeColors[d.type] || AltiusD3.colors.gray; })
            .attr('opacity', 0.85);

        // Labels
        node.append('text')
            .attr('dy', function(d) { return sizeScale(d.value) + 14; })
            .attr('text-anchor', 'middle')
            .attr('fill', AltiusD3.textColor())
            .text(function(d) { return AltiusD3.truncate(d.name, 18); });

        // Tooltips
        node.on('mouseover', function(event, d) {
            var typeLabel = d.type === 'client' ? 'Client' : 'Mandat (' + (d.type_mandat || '') + ')';
            AltiusD3.showTooltip(event,
                '<div class="tooltip-title">' + d.name + '</div>' +
                '<div class="tooltip-detail">' + typeLabel + '</div>' +
                (d.value > 0 ? '<div class="tooltip-value">' + AltiusD3.formatCurrency(d.value) + '</div>' : '')
            );
        })
        .on('mousemove', function(event) {
            var tip = document.querySelector('.d3-tooltip');
            if (tip) {
                tip.style.left = (event.pageX + 12) + 'px';
                tip.style.top = (event.pageY - 10) + 'px';
            }
        })
        .on('mouseout', function() { AltiusD3.hideTooltip(); });

        simulation.on('tick', function() {
            link
                .attr('x1', function(d) { return d.source.x; })
                .attr('y1', function(d) { return d.source.y; })
                .attr('x2', function(d) { return d.target.x; })
                .attr('y2', function(d) { return d.target.y; });
            node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
        });

        // Legend
        var legendEl = container.parentElement.querySelector('.network-legend');
        if (legendEl) {
            legendEl.innerHTML = '';
            var items = [
                { label: 'Client', color: typeColors.client },
                { label: 'Mandat', color: typeColors.mandat },
            ];
            items.forEach(function(item) {
                var div = document.createElement('div');
                div.className = 'legend-item';
                div.innerHTML = '<span class="legend-dot" style="background:' + item.color + '"></span>' + item.label;
                legendEl.appendChild(div);
            });
        }

        function dragStarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        function dragEnded(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }

    async function init() {
        AltiusD3.showLoading(container);
        try {
            var params = new URLSearchParams(window.D3_CONFIG || {});
            var url = '/analytics/api/d3/reseau-clients/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Network error:', e);
        }
    }

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });

    document.addEventListener('DOMContentLoaded', init);
    document.addEventListener('d3:refresh', init);
})();
