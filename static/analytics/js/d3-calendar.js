/**
 * Calendar Heatmap - Activité
 * Vue calendrier GitHub-style sur 12 mois.
 */
(function() {
    'use strict';

    var container = document.getElementById('calendar-container');
    if (!container) return;

    var currentData = null;
    var currentMetric = 'factures';

    var metricLabels = {
        'factures': 'Factures émises',
        'heures': 'Heures travaillées',
        'paiements': 'Paiements reçus',
    };

    var metricUnits = {
        'factures': function(d) { return d.count + ' facture(s) — ' + AltiusD3.formatCurrency(d.montant); },
        'heures': function(d) { return d.count + ' entrée(s) — ' + d.montant + 'h'; },
        'paiements': function(d) { return d.count + ' paiement(s) — ' + AltiusD3.formatCurrency(d.montant); },
    };

    function render(data) {
        currentData = data;
        container.innerHTML = '';

        var annee = data.annee || new Date().getFullYear();
        var dates = data.dates || {};

        var width = container.clientWidth;
        var cellSize = Math.max(10, Math.min(16, (width - 50) / 54));
        var height = cellSize * 7 + 40;

        var isDark = AltiusD3.isDark();

        // Color scale
        var maxVal = data.stats ? data.stats.max : 1;
        if (maxVal === 0) maxVal = 1;
        var colorScale = d3.scaleSequential(isDark ? d3.interpolateYlGn : d3.interpolateGreens)
            .domain([0, maxVal]);
        var emptyColor = isDark ? '#2d2d3f' : '#ebedf0';

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [0, 0, width, height].join(' '));

        var g = svg.append('g').attr('transform', 'translate(30, 20)');

        // Generate all days of the year
        var startDate = new Date(annee, 0, 1);
        var endDate = new Date(annee, 11, 31);
        var days = d3.timeDays(startDate, d3.timeDay.offset(endDate, 1));

        var dayOfWeek = ['Lun', '', 'Mer', '', 'Ven', '', ''];

        // Day labels
        for (var i = 0; i < 7; i++) {
            if (dayOfWeek[i]) {
                g.append('text')
                    .attr('class', 'day-label')
                    .attr('x', -5)
                    .attr('y', i * cellSize + cellSize * 0.7)
                    .attr('text-anchor', 'end')
                    .text(dayOfWeek[i]);
            }
        }

        // Month labels
        var months = d3.timeMonths(startDate, d3.timeMonth.offset(endDate, 1));
        months.forEach(function(m) {
            var week = d3.timeWeek.count(startDate, m);
            g.append('text')
                .attr('class', 'month-label')
                .attr('x', week * cellSize)
                .attr('y', -5)
                .text(d3.timeFormat('%b')(m));
        });

        // Day cells
        g.selectAll('.day')
            .data(days)
            .join('rect')
            .attr('class', 'day')
            .attr('width', cellSize - 2)
            .attr('height', cellSize - 2)
            .attr('x', function(d) {
                return d3.timeWeek.count(startDate, d) * cellSize;
            })
            .attr('y', function(d) {
                // Monday = 0
                var day = (d.getDay() + 6) % 7;
                return day * cellSize;
            })
            .attr('fill', function(d) {
                var key = d3.timeFormat('%Y-%m-%d')(d);
                var val = dates[key];
                if (!val) return emptyColor;
                return colorScale(val.montant);
            })
            .on('mouseover', function(event, d) {
                var key = d3.timeFormat('%Y-%m-%d')(d);
                var val = dates[key];
                var dateStr = d3.timeFormat('%d %B %Y')(d);
                var detail = val ? metricUnits[currentMetric](val) : 'Aucune activité';
                AltiusD3.showTooltip(event,
                    '<div class="tooltip-title">' + dateStr + '</div>' +
                    '<div class="tooltip-detail">' + detail + '</div>'
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

        // Legend
        var legendContainer = container.parentElement.querySelector('.calendar-legend');
        if (legendContainer) {
            legendContainer.innerHTML = 'Moins ';
            var steps = 5;
            for (var s = 0; s < steps; s++) {
                var span = document.createElement('span');
                span.className = 'legend-cell';
                span.style.background = s === 0 ? emptyColor : colorScale(maxVal * s / (steps - 1));
                legendContainer.appendChild(span);
            }
            legendContainer.innerHTML += ' Plus — ' + (data.stats ? data.stats.jours_actifs : 0) + ' jours actifs';
        }
    }

    async function loadData(metric) {
        currentMetric = metric || currentMetric;
        AltiusD3.showLoading(container);
        try {
            var config = window.D3_CONFIG || {};
            var params = new URLSearchParams(config);
            params.set('metric', currentMetric);
            var url = '/analytics/api/d3/calendrier-activite/?' + params.toString();
            var data = await AltiusD3.fetchJSON(url);
            render(data);
        } catch (e) {
            AltiusD3.showError(container, 'Erreur de chargement');
            console.error('Calendar error:', e);
        }
    }

    // Metric buttons
    document.addEventListener('DOMContentLoaded', function() {
        var btns = container.parentElement.querySelectorAll('.d3-metric-btn[data-metric]');
        btns.forEach(function(btn) {
            btn.addEventListener('click', function() {
                btns.forEach(function(b) { b.classList.remove('active'); });
                btn.classList.add('active');
                loadData(btn.dataset.metric);
            });
        });
        loadData('factures');
    });

    AltiusD3.onResize(container, function() { if (currentData) render(currentData); });
    AltiusD3.onThemeChange(function() { if (currentData) render(currentData); });
    document.addEventListener('d3:refresh', function() { loadData(currentMetric); });
})();
