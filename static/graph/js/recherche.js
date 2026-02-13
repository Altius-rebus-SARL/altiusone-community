/**
 * recherche.js — Recherche sémantique live via l'API pgvector
 */
(function() {
    'use strict';

    const CONFIG = window.GRAPH_CONFIG || {};
    const API_BASE = CONFIG.apiBase || '/api/v1/';
    const CSRF = CONFIG.csrfToken || '';

    const searchInput = document.getElementById('searchQuery');
    const filterType = document.getElementById('filterTypeRecherche');
    const btnRecherche = document.getElementById('btnRecherche');
    const resultsContainer = document.getElementById('searchResultsContainer');
    const resultsList = document.getElementById('resultsList');
    const resultCount = document.getElementById('resultCount');
    const loadingEl = document.getElementById('searchLoading');

    if (!searchInput || !btnRecherche) return;

    function doSearch() {
        const query = searchInput.value.trim();
        if (query.length < 2) return;

        const body = { query: query, limit: 20 };
        const typeVal = filterType?.value;
        if (typeVal) body.types = [typeVal];

        if (loadingEl) loadingEl.style.display = 'block';
        if (resultsContainer) resultsContainer.style.display = 'none';

        fetch(`${API_BASE}graph/recherche/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
            credentials: 'same-origin',
            body: JSON.stringify(body),
        })
        .then(r => r.json())
        .then(data => {
            if (loadingEl) loadingEl.style.display = 'none';
            if (resultsContainer) resultsContainer.style.display = 'block';

            const results = data.results || [];
            if (resultCount) resultCount.textContent = results.length;

            if (!results.length) {
                resultsList.innerHTML = `
                    <div class="card">
                        <div class="card-body text-center text-muted py-4">
                            Aucun résultat pour "${query}"
                        </div>
                    </div>
                `;
                return;
            }

            resultsList.innerHTML = results.map(r => `
                <div class="card mb-2">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="badge me-2" style="background:${r.couleur}20;color:${r.couleur}">
                                    <i class="ph ${r.icone} me-1"></i>${r.type_nom}
                                </span>
                                <a href="/graph/entites/${r.id}/" class="f-w-600 text-decoration-none">
                                    ${r.nom}
                                </a>
                                ${r.description ? `<p class="text-muted f-s-12 mb-0 mt-1">${r.description}</p>` : ''}
                            </div>
                            <div>
                                <span class="badge ${r.similarite >= 0.8 ? 'bg-success' : r.similarite >= 0.5 ? 'bg-warning' : 'bg-secondary'}">
                                    ${Math.round(r.similarite * 100)}%
                                </span>
                                <a href="/graph/?entite=${r.id}" class="btn btn-sm btn-light ms-1" title="Explorer">
                                    <i class="ph ph-graph"></i>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            console.error('Search error:', err);
            if (loadingEl) loadingEl.style.display = 'none';
        });
    }

    btnRecherche.addEventListener('click', doSearch);
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            doSearch();
        }
    });
})();
