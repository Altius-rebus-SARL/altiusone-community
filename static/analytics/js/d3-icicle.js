/**
 * Icicle - Décomposition Salaires
 * Diagramme icicle zoomable : Entreprise → Employés → Composantes.
 */
(function() {
    'use strict';

    var container = document.getElementById('icicle-container');
    if (!container) return;

    var breadcrumbEl = container.parentElement.querySelector('.icicle-breadcrumb');
    var currentData = null;

    var compColors = {
        'Salaire brut': '#3b82f6',
        'Salaire net': '#10b981',
        'AVS': '#ef4444',
        'LPP': '#f59e0b',
        'LAA': '#f97316',
        'AC': '#8b5cf6',
        'Impôt source': '#ec4899',
        'Allocations': '#06b6d4',
    };

    function getColor(d) {
        if (d.depth === 0) return AltiusD3.colors.primary;
        if (d.data.name in compColors) return compColors[d.data.name];
        // Assign color based on index at depth 1 (employee)
        if (d.depth === 1) {
            var idx = d.parent.children.indexOf(d);
            return AltiusD3.colors.gradient[idx % AltiusD3.colors.gradient.length];
        }
        // Inherit from parent
        if (d.parent) {
            var parentColor = d3.color(getColor(d.parent));
            return parentColor ? parentColor.brighter(0.4).toString() : AltiusD3.colors.gray;
        }
        return AltiusD3.colors.gray;
    }

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        if (!data || !data.children || data.children.length === 0) {
            AltiusD3.showEmpty(container, 'ph ph-chart-bar', 'Aucune fiche de salaire');
            return;
        }

        var width = container.clientWidth;
        var height = Math.max(400, container.clientHeight || 450);

        var root = d3.hierarchy(data)
            .sum(function(d) { return d.children ? 0 : d.value; })
            .sort(function(a, b) { return b.value - a.value; });

        d3.partition()
            .size([width, height])
            .padding(1)(root);

        var focus = root;

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [0, 0, width, height].join(' '))
            .style('font', '10px Rubik, sans-serif');

        var cell = svg.selectAll('g')
            .data(root.descendants())
            .join('g')
            .attr('transform', function(d) { return 'translate(' + d.x0 + ',' + d.y0 + ')'; });

        cell.append('rect')
            .attr('class', 'cell')
            .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
            .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); })
            .attr('fill', getColor)
            .on('mouseover', function(event, d) {
                var ancestors = d.ancestors().reverse().slice(1);
                if (breadcrumbEl) {
                    breadcrumbEl.innerHTML = ancestors.map(function(a) {
                        return '<span>' + a.data.name + '</span>';
                    }).join(' → ');
                }
                AltiusD3.showTooltip(event,
                    '<div class="tooltip-title">' + d.data.name + '</div>' +
                    '<div class="tooltip-value">' + AltiusD3.formatCurrency(d.value) + '</div>' +
                    (d.parent ? '<div class="tooltip-detail">' +
                        AltiusD3.formatPercent(d.value / d.parent.value * 100) +
                        ' du parent</div>' : '')
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
                if (breadcrumbEl) breadcrumbEl.textContent = '';
                AltiusD3.hideTooltip();
            })
            .on('click', function(event, d) {
                if (d === focus) {
                    focus = d.parent || root;
                } else {
                    focus = d;
                }
                zoomTo(focus, svg, cell, root, width, height);
            });

        // Labels
        cell.append('text')
            .attr('class', 'cell-label')
            .attr('x', 4)
            .attr('y', 14)
            .text(function(d) {
                var w = d.x1 - d.x0;
                var h = d.y1 - d.y0;
                if (w < 40 || h < 16) return '';
                var maxChars = Math.floor(w / 7);
                return AltiusD3.truncate(d.data.name, maxChars);
            });

        // Value labels
        cell.append('text')
            .attr('class', 'cell-label')
            .attr('x', 4)
            .attr('y', 28)
            .attr('opacity', 0.8)
            .text(function(d) {
                var w = d.x1 - d.x0;
                var h = d.y1 - d.y0;
                if (w < 60 || h < 32) return '';
                return AltiusD3.formatCurrency(d.value);
            });
    }

    function zoomTo(focus, svg, cell, root, width, height) {
        var x0 = focus.x0;
        var x1 = focus.x1;
        var y0 = focus.y0;
        var y1 = focus.depth === 0 ? height : focus.y1;

        var kx = width / (x1 - x0);
        var ky = height / (y1 - y0);

        var t = svg.transition().duration(500);

        cell.transition(t)
            .attr('transform', function(d) {
                return 'translate(' + ((d.x0 - x0) * kx) + ',' + ((d.y0 - y0) * ky) + ')';
            });

        cell.select('rect').transition(t)
            .attr('width', function(d) { return Math.max(0, (d.x1 - d.x0) * kx); })
            .attr('height', function(d) { return Math.max(0, (d.y1 - d.y0) * ky); });

        cell.selectAll('text').transition(t)
            .attr('opacity', function(d) {
                var w = (d.x1 - d.x0) * kx;
                var h = (d.y1 - d.y0) * ky;
                return (w > 40 && h > 16) ? 1 : 0;
            });
    }

    async function init() {
        AltiusD3.showLoading(container);
        try {
            var config = window.D3_CONFIG || {};
            var params = new URLSearchParams(config);
            var moisSelect = document.getElementById('icicle-mois');
            if (moisSelect && moisSelect.value) {
                params.set('mois', moisSelect.value);
            }
            var url = '/analytics/api/d3/decomposition-salaires/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Icicle error:', e);
        }
    }

    // Month filter
    document.addEventListener('DOMContentLoaded', function() {
        var moisSelect = document.getElementById('icicle-mois');
        if (moisSelect) {
            moisSelect.addEventListener('change', init);
        }
        init();
    });

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });
    document.addEventListener('d3:refresh', init);
})();
