/**
 * Sankey - Flux Trésorerie
 * Diagramme de flux revenus → dépenses.
 */
(function() {
    'use strict';

    var container = document.getElementById('sankey-container');
    if (!container) return;

    var currentData = null;

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        if (!data || !data.nodes || data.nodes.length === 0 || !data.links || data.links.length === 0) {
            AltiusD3.showEmpty(container, 'ph ph-flow-arrow', 'Aucun flux de trésorerie');
            return;
        }

        var width = container.clientWidth;
        var height = Math.max(400, container.clientHeight || 450);
        var margin = { top: 10, right: 150, bottom: 10, left: 10 };
        var innerWidth = width - margin.left - margin.right;
        var innerHeight = height - margin.top - margin.bottom;

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [0, 0, width, height].join(' '));

        var g = svg.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

        var sankey = d3.sankey()
            .nodeId(function(d, i) { return i; })
            .nodeWidth(20)
            .nodePadding(12)
            .nodeAlign(d3.sankeyJustify)
            .extent([[0, 0], [innerWidth, innerHeight]]);

        var graph = sankey({
            nodes: data.nodes.map(function(d) { return Object.assign({}, d); }),
            links: data.links.map(function(d) { return Object.assign({}, d); }),
        });

        // Links
        g.append('g')
            .selectAll('.link')
            .data(graph.links)
            .join('path')
            .attr('class', 'link')
            .attr('d', d3.sankeyLinkHorizontal())
            .attr('stroke', function(d) {
                return d.source.color || AltiusD3.colors.primary;
            })
            .attr('stroke-width', function(d) { return Math.max(2, d.width); })
            .on('mouseover', function(event, d) {
                d3.select(this).attr('stroke-opacity', 0.6);
                AltiusD3.showTooltip(event,
                    '<div class="tooltip-title">' + d.source.name + ' → ' + d.target.name + '</div>' +
                    '<div class="tooltip-value">' + AltiusD3.formatCurrency(d.value) + '</div>'
                );
            })
            .on('mousemove', function(event) {
                var tip = document.querySelector('.d3-tooltip');
                if (tip) {
                    tip.style.left = (event.pageX + 12) + 'px';
                    tip.style.top = (event.pageY - 10) + 'px';
                }
            })
            .on('mouseout', function() {
                d3.select(this).attr('stroke-opacity', 0.3);
                AltiusD3.hideTooltip();
            });

        // Nodes
        var node = g.append('g')
            .selectAll('.node')
            .data(graph.nodes)
            .join('g')
            .attr('class', 'node');

        node.append('rect')
            .attr('x', function(d) { return d.x0; })
            .attr('y', function(d) { return d.y0; })
            .attr('height', function(d) { return Math.max(1, d.y1 - d.y0); })
            .attr('width', function(d) { return d.x1 - d.x0; })
            .attr('fill', function(d) { return d.color || AltiusD3.colors.gray; })
            .on('mouseover', function(event, d) {
                AltiusD3.showTooltip(event,
                    '<div class="tooltip-title">' + d.name + '</div>' +
                    '<div class="tooltip-value">' + AltiusD3.formatCurrency(d.value) + '</div>'
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

        // Labels
        node.append('text')
            .attr('x', function(d) { return d.x0 < innerWidth / 2 ? d.x1 + 6 : d.x0 - 6; })
            .attr('y', function(d) { return (d.y0 + d.y1) / 2; })
            .attr('dy', '0.35em')
            .attr('text-anchor', function(d) { return d.x0 < innerWidth / 2 ? 'start' : 'end'; })
            .attr('fill', AltiusD3.textColor())
            .text(function(d) {
                return d.name + ' (' + AltiusD3.formatCurrency(d.value) + ')';
            });
    }

    async function init() {
        AltiusD3.showLoading(container);
        try {
            var params = new URLSearchParams(window.D3_CONFIG || {});
            var url = '/analytics/api/d3/flux-tresorerie/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Sankey error:', e);
        }
    }

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });

    document.addEventListener('DOMContentLoaded', init);
    document.addEventListener('d3:refresh', init);
})();
