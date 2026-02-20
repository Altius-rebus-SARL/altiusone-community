/**
 * Timeline Gantt - Projets & Opérations
 * Diagramme de Gantt avec barres horizontales et zoom temporel.
 */
(function() {
    'use strict';

    var container = document.getElementById('timeline-container');
    if (!container) return;

    var currentData = null;

    var statutColors = {
        'PLANIFIE': AltiusD3.colors.info,
        'A_FAIRE': '#94a3b8',
        'EN_COURS': AltiusD3.colors.primary,
        'EN_ATTENTE': AltiusD3.colors.warning,
        'TERMINEE': AltiusD3.colors.success,
        'TERMINE': AltiusD3.colors.success,
    };

    var prioriteIcons = {
        'CRITIQUE': '!!',
        'HAUTE': '!',
        'NORMALE': '',
        'BASSE': '',
    };

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        if (!data || !data.projets || data.projets.length === 0) {
            AltiusD3.showEmpty(container, 'ph ph-calendar-blank', 'Aucun projet en cours');
            return;
        }

        // Flatten: project rows + operation rows
        var rows = [];
        data.projets.forEach(function(p) {
            rows.push({ type: 'projet', data: p, level: 0 });
            (p.operations || []).forEach(function(op) {
                rows.push({ type: 'operation', data: op, level: 1, projet: p });
            });
        });

        var width = container.clientWidth;
        var rowHeight = 28;
        var margin = { top: 30, right: 20, bottom: 30, left: 250 };
        var innerWidth = width - margin.left - margin.right;
        var innerHeight = rows.length * rowHeight;
        var height = innerHeight + margin.top + margin.bottom;

        // Time scale
        var dateMin = new Date(data.date_min);
        var dateMax = new Date(data.date_max);
        // Add padding
        var dayPad = Math.max(7, Math.round((dateMax - dateMin) / (1000 * 60 * 60 * 24) * 0.05));
        dateMin = d3.timeDay.offset(dateMin, -dayPad);
        dateMax = d3.timeDay.offset(dateMax, dayPad);

        var x = d3.scaleTime().domain([dateMin, dateMax]).range([0, innerWidth]);

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [0, 0, width, height].join(' '))
            .style('font', '11px Rubik, sans-serif');

        // Clip path
        svg.append('defs').append('clipPath')
            .attr('id', 'timeline-clip')
            .append('rect')
            .attr('width', innerWidth)
            .attr('height', innerHeight);

        var g = svg.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

        // Grid lines
        var xAxis = d3.axisTop(x)
            .ticks(d3.timeWeek.every(1))
            .tickFormat(d3.timeFormat('%d %b'));

        g.append('g')
            .attr('class', 'axis')
            .call(xAxis)
            .selectAll('text')
            .attr('transform', 'rotate(-30)')
            .attr('text-anchor', 'end');

        // Vertical grid
        g.append('g')
            .selectAll('.grid-line')
            .data(x.ticks(d3.timeWeek.every(1)))
            .join('line')
            .attr('class', 'grid-line')
            .attr('x1', function(d) { return x(d); })
            .attr('x2', function(d) { return x(d); })
            .attr('y1', 0)
            .attr('y2', innerHeight);

        // Today line
        var today = new Date();
        if (today >= dateMin && today <= dateMax) {
            g.append('line')
                .attr('class', 'today-line')
                .attr('x1', x(today))
                .attr('x2', x(today))
                .attr('y1', 0)
                .attr('y2', innerHeight);
            g.append('text')
                .attr('x', x(today))
                .attr('y', -5)
                .attr('text-anchor', 'middle')
                .attr('fill', AltiusD3.colors.danger)
                .attr('font-size', '9px')
                .text("Aujourd'hui");
        }

        // Bars group with clip
        var barsGroup = g.append('g').attr('clip-path', 'url(#timeline-clip)');

        // Row labels (left side)
        var labelsG = svg.append('g')
            .attr('transform', 'translate(0,' + margin.top + ')');

        rows.forEach(function(row, i) {
            var y = i * rowHeight;
            var d = row.data;
            var dStart = d.date_debut ? new Date(d.date_debut) : null;
            var dEnd = d.date_fin ? new Date(d.date_fin) : null;

            // Alternating row background
            if (i % 2 === 0) {
                barsGroup.append('rect')
                    .attr('x', 0)
                    .attr('y', y)
                    .attr('width', innerWidth)
                    .attr('height', rowHeight)
                    .attr('fill', AltiusD3.isDark() ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)');
            }

            // Label
            var labelX = row.level === 0 ? 8 : 24;
            var label = row.level === 0 ? d.nom : d.titre;
            var fontWeight = row.level === 0 ? 600 : 400;

            labelsG.append('text')
                .attr('class', 'bar-label')
                .attr('x', labelX)
                .attr('y', y + rowHeight / 2 + 4)
                .attr('font-weight', fontWeight)
                .attr('fill', AltiusD3.textColor())
                .text(AltiusD3.truncate(label, 30));

            // Bar
            if (dStart && dEnd) {
                var barX = x(dStart);
                var barW = Math.max(4, x(dEnd) - x(dStart));
                var color = statutColors[d.statut] || AltiusD3.colors.gray;

                barsGroup.append('rect')
                    .attr('class', 'bar')
                    .attr('x', barX)
                    .attr('y', y + 4)
                    .attr('width', barW)
                    .attr('height', rowHeight - 8)
                    .attr('fill', color)
                    .attr('opacity', row.level === 0 ? 0.4 : 0.75)
                    .on('mouseover', function(event) {
                        var statut = d.statut || '-';
                        var dateRange = d3.timeFormat('%d.%m.%Y')(dStart) + ' → ' + d3.timeFormat('%d.%m.%Y')(dEnd);
                        AltiusD3.showTooltip(event,
                            '<div class="tooltip-title">' + (d.titre || d.nom) + '</div>' +
                            '<div class="tooltip-detail">' + dateRange + '</div>' +
                            '<div class="tooltip-detail">Statut: ' + statut + '</div>'
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

                // Priority icon
                if (d.priorite && prioriteIcons[d.priorite]) {
                    barsGroup.append('text')
                        .attr('x', barX + barW + 4)
                        .attr('y', y + rowHeight / 2 + 4)
                        .attr('fill', d.priorite === 'CRITIQUE' ? AltiusD3.colors.danger : AltiusD3.colors.warning)
                        .attr('font-size', '10px')
                        .attr('font-weight', 700)
                        .text(prioriteIcons[d.priorite]);
                }
            }
        });

        // Brush for zoom
        var brush = d3.brushX()
            .extent([[0, 0], [innerWidth, innerHeight]])
            .on('end', function(event) {
                if (!event.selection) return;
                var s = event.selection;
                var newDomain = [x.invert(s[0]), x.invert(s[1])];
                x.domain(newDomain);

                // Remove brush selection
                g.select('.brush').call(brush.move, null);

                // Re-render bars with new x domain
                updateBars();
                g.select('.axis').call(xAxis);
            });

        g.append('g')
            .attr('class', 'brush')
            .call(brush);

        function updateBars() {
            barsGroup.selectAll('.bar').each(function(d, i) {
                var row = rows[i];
                if (!row) return;
                var rd = row.data;
                var dStart = rd.date_debut ? new Date(rd.date_debut) : null;
                var dEnd = rd.date_fin ? new Date(rd.date_fin) : null;
                if (dStart && dEnd) {
                    d3.select(this)
                        .attr('x', x(dStart))
                        .attr('width', Math.max(4, x(dEnd) - x(dStart)));
                }
            });
        }
    }

    async function init() {
        AltiusD3.showLoading(container);
        try {
            var params = new URLSearchParams(window.D3_CONFIG || {});
            var url = '/analytics/api/d3/timeline-projets/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Timeline error:', e);
        }
    }

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });

    document.addEventListener('DOMContentLoaded', init);
    document.addEventListener('d3:refresh', init);
})();
