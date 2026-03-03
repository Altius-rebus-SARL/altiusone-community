/**
 * timeline.js — D3.js brush pour filtrer les relations par période
 */
(function() {
    'use strict';

    const container = document.getElementById('timelineContainer');
    if (!container) return;

    const width = container.clientWidth;
    const height = 50;
    const margin = { top: 5, right: 20, bottom: 20, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select('#timelineContainer')
        .append('svg')
        .attr('width', '100%')
        .attr('height', height);

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Default range: 5 years
    const now = new Date();
    const fiveYearsAgo = new Date(now.getFullYear() - 5, 0, 1);

    const x = d3.scaleTime()
        .domain([fiveYearsAgo, now])
        .range([0, innerWidth]);

    // Axis
    g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y')))
        .selectAll('text')
        .attr('font-size', '10px');

    // Brush
    const brush = d3.brushX()
        .extent([[0, 0], [innerWidth, innerHeight]])
        .on('end', brushed);

    g.append('g')
        .attr('class', 'brush')
        .call(brush);

    function brushed(event) {
        if (!event.selection) return;
        const [x0, x1] = event.selection.map(x.invert);

        // Dispatch custom event for the graph to pick up
        const detail = {
            dateMin: x0.toISOString().split('T')[0],
            dateMax: x1.toISOString().split('T')[0],
        };
        container.dispatchEvent(new CustomEvent('timeline:filter', { detail }));
    }
})();
