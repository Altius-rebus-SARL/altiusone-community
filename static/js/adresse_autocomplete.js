/**
 * Auto-complétion d'adresses suisses via Swiss Post API.
 *
 * Usage:
 *   initAdresseAutocomplete({
 *       prefix: 'id_adresse',           // Préfixe des IDs des champs
 *       triggerSelector: null,           // Sélecteur optionnel du champ déclencheur (défaut: prefix-rue)
 *       fieldMap: null,                  // Mapping personnalisé { street, house_number, zip_code, city, canton }
 *   });
 */
function initAdresseAutocomplete(options) {
    'use strict';

    var prefix = options.prefix || 'id_adresse';
    var debounceMs = 300;
    var minChars = 3;
    var apiUrl = '/api/v1/adresses/autocomplete/';

    // Résolution des champs avec le mapping par défaut ou personnalisé
    var fieldMap = options.fieldMap || {
        street: prefix + '-rue',
        house_number: prefix + '-numero',
        zip_code: prefix + '-code_postal',
        city: prefix + '-localite',
        canton: prefix + '-canton',
    };

    var streetInput = document.getElementById(options.triggerSelector || fieldMap.street);
    if (!streetInput) return;

    var houseInput = document.getElementById(fieldMap.house_number);
    var zipInput = document.getElementById(fieldMap.zip_code);
    var cityInput = document.getElementById(fieldMap.city);
    var cantonInput = document.getElementById(fieldMap.canton);

    // Créer le conteneur de résultats
    var container = streetInput.parentElement;
    container.style.position = 'relative';

    var resultsDiv = document.createElement('div');
    resultsDiv.className = 'adresse-autocomplete-results';
    resultsDiv.style.cssText = 'position:absolute;top:100%;left:0;right:0;z-index:1050;' +
        'background:var(--bs-body-bg,#fff);border:1px solid var(--bs-border-color,#dee2e6);' +
        'border-top:none;border-radius:0 0 .375rem .375rem;max-height:250px;overflow-y:auto;' +
        'display:none;box-shadow:0 4px 6px rgba(0,0,0,.1);';
    container.appendChild(resultsDiv);

    var debounceTimer = null;
    var currentResults = [];
    var selectedIndex = -1;

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showResults() { resultsDiv.style.display = 'block'; }
    function hideResults() { resultsDiv.style.display = 'none'; selectedIndex = -1; }

    function fetchAddresses(query) {
        if (query.length < minChars) { hideResults(); return; }

        resultsDiv.innerHTML = '<div style="padding:.75rem 1rem;text-align:center;color:#6c757d;">' +
            '<i class="ph ph-spinner ph-spin me-2"></i>Recherche...</div>';
        showResults();

        fetch(apiUrl + '?q=' + encodeURIComponent(query), {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        })
        .then(function(r) {
            if (!r.ok) throw new Error('Network error');
            return r.json();
        })
        .then(function(data) {
            currentResults = data.results || [];
            renderResults(currentResults);
        })
        .catch(function(err) {
            console.error('Address autocomplete error:', err);
            resultsDiv.innerHTML = '<div style="padding:.75rem 1rem;text-align:center;color:#6c757d;font-style:italic;">Erreur de recherche</div>';
        });
    }

    function renderResults(addresses) {
        if (addresses.length === 0) {
            resultsDiv.innerHTML = '<div style="padding:.75rem 1rem;text-align:center;color:#6c757d;font-style:italic;">Aucun résultat</div>';
            showResults();
            return;
        }

        var html = '';
        addresses.forEach(function(addr, i) {
            var line1 = escapeHtml(addr.street);
            if (addr.house_number) line1 += ' ' + escapeHtml(addr.house_number);
            var line2 = escapeHtml(addr.zip_code) + ' ' + escapeHtml(addr.city);
            if (addr.canton) line2 += ' (' + escapeHtml(addr.canton) + ')';

            html += '<div class="adresse-ac-item" data-index="' + i + '" style="' +
                'padding:.5rem .75rem;cursor:pointer;border-bottom:1px solid #eee;">' +
                '<div style="font-weight:600;">' + line1 + '</div>' +
                '<div style="font-size:.85rem;color:#6c757d;">' + line2 + '</div>' +
                '</div>';
        });

        resultsDiv.innerHTML = html;
        showResults();

        resultsDiv.querySelectorAll('.adresse-ac-item').forEach(function(item) {
            item.addEventListener('click', function() {
                selectAddress(parseInt(this.dataset.index));
            });
            item.addEventListener('mouseenter', function() {
                resultsDiv.querySelectorAll('.adresse-ac-item').forEach(function(el) {
                    el.style.backgroundColor = '';
                });
                this.style.backgroundColor = 'var(--bs-primary-bg-subtle, #e7f1ff)';
                selectedIndex = parseInt(this.dataset.index);
            });
        });
    }

    function selectAddress(index) {
        var addr = currentResults[index];
        if (!addr) return;

        if (streetInput) {
            // Si pas de champ numéro séparé, concaténer rue + numéro
            if (!houseInput && addr.house_number) {
                streetInput.value = (addr.street || '') + ' ' + addr.house_number;
            } else {
                streetInput.value = addr.street || '';
            }
        }
        if (houseInput) houseInput.value = addr.house_number || '';
        if (zipInput) zipInput.value = addr.zip_code || '';
        if (cityInput) cityInput.value = addr.city || '';

        if (cantonInput && addr.canton) {
            // Support both <select> and <input>
            if (cantonInput.tagName === 'SELECT') {
                var opt = cantonInput.querySelector('option[value="' + addr.canton + '"]');
                if (opt) cantonInput.value = addr.canton;
            } else {
                cantonInput.value = addr.canton;
            }
        }

        hideResults();

        // Visual feedback
        var filledFields = [streetInput, houseInput, zipInput, cityInput, cantonInput].filter(function(f) {
            return f && f.value;
        });
        filledFields.forEach(function(f) { f.classList.add('is-valid'); });
        setTimeout(function() {
            filledFields.forEach(function(f) { f.classList.remove('is-valid'); });
        }, 2000);
    }

    // Input event with debounce
    streetInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        var val = this.value.trim();
        debounceTimer = setTimeout(function() { fetchAddresses(val); }, debounceMs);
    });

    // Keyboard navigation
    streetInput.addEventListener('keydown', function(e) {
        var items = resultsDiv.querySelectorAll('.adresse-ac-item');
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            updateSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, 0);
            updateSelection(items);
        } else if (e.key === 'Enter' && selectedIndex >= 0) {
            e.preventDefault();
            selectAddress(selectedIndex);
        } else if (e.key === 'Escape') {
            hideResults();
        }
    });

    function updateSelection(items) {
        items.forEach(function(item, i) {
            item.style.backgroundColor = (i === selectedIndex)
                ? 'var(--bs-primary-bg-subtle, #e7f1ff)' : '';
            if (i === selectedIndex) item.scrollIntoView({ block: 'nearest' });
        });
    }

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!streetInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            hideResults();
        }
    });

    // Re-show on focus if results exist
    streetInput.addEventListener('focus', function() {
        if (currentResults.length > 0 && this.value.length >= minChars) {
            showResults();
        }
    });
}
