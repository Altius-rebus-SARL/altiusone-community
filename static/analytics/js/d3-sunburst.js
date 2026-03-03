/**
 * Sunburst - Plan Comptable
 * Arbre interactif du plan comptable avec soldes.
 */
(function() {
    'use strict';

    var container = document.getElementById('sunburst-container');
    if (!container) return;

    var breadcrumbEl = container.parentElement.querySelector('.sunburst-breadcrumb');
    var currentData = null;
    var currentRoot = null;

    var typeColors = {
        'ACTIF': AltiusD3.colors.actif,
        'PASSIF': AltiusD3.colors.passif,
        'CHARGE': AltiusD3.colors.danger,
        'PRODUIT': AltiusD3.colors.success,
    };

    function getColor(d) {
        if (d.data.type_compte && typeColors[d.data.type_compte]) {
            return typeColors[d.data.type_compte];
        }
        // Inherit from ancestors
        var node = d;
        while (node.parent) {
            node = node.parent;
            if (node.data.type_compte && typeColors[node.data.type_compte]) {
                var base = d3.color(typeColors[node.data.type_compte]);
                return base.brighter(d.depth * 0.3).toString();
            }
        }
        return AltiusD3.colors.gray;
    }

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        if (!data || !data.children || data.children.length === 0) {
            AltiusD3.showEmpty(container, 'ph ph-chart-pie-slice', 'Aucune donnée comptable');
            return;
        }

        var width = container.clientWidth;
        var height = Math.max(400, container.clientHeight || 450);
        var radius = Math.min(width, height) / 2;

        var root = d3.hierarchy(data)
            .sum(function(d) { return d.children ? 0 : d.value; })
            .sort(function(a, b) { return b.value - a.value; });

        d3.partition()
            .size([2 * Math.PI, radius])(root);

        currentRoot = root;

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [-width / 2, -height / 2, width, height].join(' '))
            .style('font', '10px Rubik, sans-serif');

        var arc = d3.arc()
            .startAngle(function(d) { return d.x0; })
            .endAngle(function(d) { return d.x1; })
            .padAngle(function(d) { return Math.min((d.x1 - d.x0) / 2, 0.005); })
            .padRadius(radius / 2)
            .innerRadius(function(d) { return d.y0; })
            .outerRadius(function(d) { return d.y1 - 1; });

        var path = svg.selectAll('path')
            .data(root.descendants().filter(function(d) { return d.depth; }))
            .join('path')
            .attr('class', 'arc')
            .attr('fill', getColor)
            .attr('d', arc);

        path.on('mouseover', function(event, d) {
            var ancestors = d.ancestors().reverse().slice(1);
            var breadcrumb = ancestors.map(function(a) { return a.data.name; }).join(' → ');
            if (breadcrumbEl) breadcrumbEl.textContent = breadcrumb;

            AltiusD3.showTooltip(event,
                '<div class="tooltip-title">' + d.data.name + '</div>' +
                '<div class="tooltip-value">' + AltiusD3.formatCurrency(d.value) + '</div>' +
                (d.data.type_compte ? '<div class="tooltip-detail">' + d.data.type_compte + '</div>' : '')
            );
        })
        .on('mousemove', function(event) {
            AltiusD3.showTooltip(event, AltiusD3.getTooltip ? '' : '');
            // Re-position
            var tip = document.querySelector('.d3-tooltip');
            if (tip) {
                tip.style.left = (event.pageX + 12) + 'px';
                tip.style.top = (event.pageY - 10) + 'px';
            }
        })
        .on('mouseout', function() {
            if (breadcrumbEl) breadcrumbEl.textContent = '';
            AltiusD3.hideTooltip();
        })
        .on('click', function(event, d) {
            zoomTo(d, svg, arc, path, root, radius);
        });

        // Labels for larger arcs
        svg.selectAll('text')
            .data(root.descendants().filter(function(d) {
                return d.depth && (d.x1 - d.x0) > 0.05 && d.depth <= 2;
            }))
            .join('text')
            .attr('class', 'label')
            .attr('transform', function(d) {
                var x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
                var y = (d.y0 + d.y1) / 2;
                return 'rotate(' + (x - 90) + ') translate(' + y + ',0) rotate(' + (x < 180 ? 0 : 180) + ')';
            })
            .attr('text-anchor', 'middle')
            .attr('fill', AltiusD3.textColor())
            .text(function(d) {
                return AltiusD3.truncate(d.data.numero || d.data.name, 12);
            });
    }

    function zoomTo(d, svg, arc, path, root, radius) {
        var parent = d.parent || root;
        var target = d === currentRoot ? root : d;

        currentRoot = target;

        var t = svg.transition().duration(750);

        // Tween arcs
        path.transition(t)
            .tween('data', function(dd) {
                var x0i = d3.interpolate(dd.x0, Math.max(0, Math.min(2 * Math.PI, (dd.x0 - target.x0) / (target.x1 - target.x0) * 2 * Math.PI)));
                var x1i = d3.interpolate(dd.x1, Math.max(0, Math.min(2 * Math.PI, (dd.x1 - target.x0) / (target.x1 - target.x0) * 2 * Math.PI)));
                var y0i = d3.interpolate(dd.y0, Math.max(0, dd.y0 - target.y0));
                var y1i = d3.interpolate(dd.y1, Math.max(0, dd.y1 - target.y0));
                return function(t) {
                    dd.x0 = x0i(t);
                    dd.x1 = x1i(t);
                    dd.y0 = y0i(t);
                    dd.y1 = y1i(t);
                };
            })
            .attrTween('d', function(dd) {
                return function() { return arc(dd); };
            })
            .attr('fill-opacity', function(dd) {
                return dd.x1 - dd.x0 > 0.005 ? 1 : 0;
            });
    }

    async function init() {
        AltiusD3.showLoading(container);
        try {
            var params = new URLSearchParams(window.D3_CONFIG || {});
            var url = '/analytics/api/d3/plan-comptable/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Sunburst error:', e);
        }
    }

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });

    document.addEventListener('DOMContentLoaded', init);
    // Listen for filter changes
    document.addEventListener('d3:refresh', init);
})();
