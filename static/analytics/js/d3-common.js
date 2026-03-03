/**
 * AltiusOne D3.js - Utilitaires partagés
 * Tooltip, formatage, couleurs, responsive, dark mode
 */
const AltiusD3 = (function() {
    'use strict';

    // Palette de couleurs (alignée sur AltiusCharts)
    const colors = {
        primary: '#3b82f6',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#06b6d4',
        purple: '#8b5cf6',
        pink: '#ec4899',
        gray: '#6b7280',
        gradient: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'],
        // Couleurs comptables
        actif: '#3b82f6',
        passif: '#8b5cf6',
        charge: '#ef4444',
        produit: '#10b981',
    };

    // Devise depuis le context global
    function getDevise() {
        if (window.ALTIUSONE_DEVISE) {
            return { code: window.ALTIUSONE_DEVISE.code, taux: window.ALTIUSONE_DEVISE.taux };
        }
        return { code: window.ALTIUSONE_DEVISE?.base || 'CHF', taux: 1 };
    }

    // Formatage monétaire (fr-CH)
    function formatCurrency(value, decimals) {
        if (decimals === undefined) decimals = 0;
        var devise = getDevise();
        var converted = value * devise.taux;
        return new Intl.NumberFormat('fr-CH', {
            style: 'currency',
            currency: devise.code,
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(converted);
    }

    // Formatage nombre
    function formatNumber(value, decimals) {
        if (decimals === undefined) decimals = 0;
        return new Intl.NumberFormat('fr-CH', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(value);
    }

    // Formatage pourcentage
    function formatPercent(value, decimals) {
        if (decimals === undefined) decimals = 1;
        return new Intl.NumberFormat('fr-CH', {
            style: 'percent',
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(value / 100);
    }

    // Dark mode
    function isDark() {
        return document.documentElement.classList.contains('dark');
    }

    // Couleurs de texte selon theme
    function textColor() { return isDark() ? '#e5e7eb' : '#374151'; }
    function mutedColor() { return isDark() ? '#9ca3af' : '#6b7280'; }
    function gridColor() { return isDark() ? '#374151' : '#e5e7eb'; }
    function bgColor() { return isDark() ? '#1e1e2e' : '#ffffff'; }

    // Tooltip management
    var tooltipEl = null;

    function getTooltip() {
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.className = 'd3-tooltip';
            document.body.appendChild(tooltipEl);
        }
        return tooltipEl;
    }

    function showTooltip(event, html) {
        var tip = getTooltip();
        tip.innerHTML = html;
        tip.classList.add('visible');

        var x = event.pageX + 12;
        var y = event.pageY - 10;

        // Prevent overflow right
        if (x + tip.offsetWidth > window.innerWidth - 20) {
            x = event.pageX - tip.offsetWidth - 12;
        }
        // Prevent overflow bottom
        if (y + tip.offsetHeight > window.scrollY + window.innerHeight - 20) {
            y = event.pageY - tip.offsetHeight - 10;
        }

        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
    }

    function hideTooltip() {
        var tip = getTooltip();
        tip.classList.remove('visible');
    }

    // Debounce
    function debounce(fn, delay) {
        var timer;
        return function() {
            var ctx = this, args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function() { fn.apply(ctx, args); }, delay);
        };
    }

    // Fetch JSON avec CSRF
    function fetchJSON(url) {
        return fetch(url, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' },
        }).then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    // Afficher loading
    function showLoading(container) {
        container.innerHTML =
            '<div class="d3-loading">' +
                '<div class="spinner-border text-primary" role="status">' +
                    '<span class="visually-hidden">Chargement...</span>' +
                '</div>' +
            '</div>';
    }

    // Afficher empty
    function showEmpty(container, icon, message) {
        container.innerHTML =
            '<div class="d3-empty">' +
                '<i class="' + icon + '"></i>' +
                '<p>' + message + '</p>' +
            '</div>';
    }

    // Afficher erreur
    function showError(container, message) {
        container.innerHTML =
            '<div class="d3-error">' +
                '<i class="ph ph-warning-circle"></i>' +
                '<p>' + (message || 'Erreur de chargement') + '</p>' +
            '</div>';
    }

    // Responsive: observer le resize du conteneur
    function onResize(element, callback) {
        var debouncedCb = debounce(callback, 250);
        if (window.ResizeObserver) {
            var ro = new ResizeObserver(debouncedCb);
            ro.observe(element);
            return ro;
        }
        window.addEventListener('resize', debouncedCb);
        return null;
    }

    // Theme change listener
    function onThemeChange(callback) {
        var observer = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].attributeName === 'class') {
                    callback(isDark());
                    return;
                }
            }
        });
        observer.observe(document.documentElement, { attributes: true });
        return observer;
    }

    // Color scale from data domain
    function colorScaleSequential(domain, interpolator) {
        return d3.scaleSequential(interpolator || d3.interpolateBlues).domain(domain);
    }

    // Truncate text
    function truncate(text, maxLen) {
        if (!text) return '';
        if (maxLen === undefined) maxLen = 20;
        return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
    }

    return {
        colors: colors,
        getDevise: getDevise,
        formatCurrency: formatCurrency,
        formatNumber: formatNumber,
        formatPercent: formatPercent,
        isDark: isDark,
        textColor: textColor,
        mutedColor: mutedColor,
        gridColor: gridColor,
        bgColor: bgColor,
        showTooltip: showTooltip,
        hideTooltip: hideTooltip,
        debounce: debounce,
        fetchJSON: fetchJSON,
        showLoading: showLoading,
        showEmpty: showEmpty,
        showError: showError,
        onResize: onResize,
        onThemeChange: onThemeChange,
        colorScaleSequential: colorScaleSequential,
        truncate: truncate,
    };
})();
