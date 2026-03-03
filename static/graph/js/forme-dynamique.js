/**
 * forme-dynamique.js — Génère les champs de formulaire dynamiques
 * depuis le schema_attributs du type d'ontologie sélectionné.
 */
(function() {
    'use strict';

    const typeSelect = document.getElementById('id_type');
    const dynamicSection = document.getElementById('dynamicAttributs');
    const dynamicFields = document.getElementById('dynamicFields');
    if (!typeSelect || !dynamicSection || !dynamicFields) return;

    const CONFIG = window.GRAPH_CONFIG || {};
    const API_BASE = CONFIG.apiBase || '/api/v1/';

    typeSelect.addEventListener('change', function() {
        const typeId = this.value;
        if (!typeId) {
            dynamicSection.style.display = 'none';
            dynamicFields.innerHTML = '';
            return;
        }

        fetch(`${API_BASE}graph-types/${typeId}/`, {
            credentials: 'same-origin',
        })
        .then(r => r.json())
        .then(data => {
            const schema = data.schema_attributs || {};
            if (!Object.keys(schema).length) {
                dynamicSection.style.display = 'none';
                dynamicFields.innerHTML = '';
                return;
            }

            dynamicSection.style.display = 'block';
            dynamicFields.innerHTML = '';

            for (const [key, config] of Object.entries(schema)) {
                const col = document.createElement('div');
                col.className = 'col-md-6 mb-3';

                const label = document.createElement('label');
                label.className = 'form-label';
                label.textContent = config.label || key;
                if (config.required) {
                    const req = document.createElement('span');
                    req.className = 'text-danger';
                    req.textContent = ' *';
                    label.appendChild(req);
                }

                let input;
                const fieldType = config.type || 'text';

                switch (fieldType) {
                    case 'textarea':
                        input = document.createElement('textarea');
                        input.rows = 3;
                        break;
                    case 'select':
                        input = document.createElement('select');
                        const emptyOpt = document.createElement('option');
                        emptyOpt.value = '';
                        emptyOpt.textContent = '---';
                        input.appendChild(emptyOpt);
                        (config.choices || []).forEach(c => {
                            const opt = document.createElement('option');
                            opt.value = c;
                            opt.textContent = c;
                            input.appendChild(opt);
                        });
                        input.className = 'form-select';
                        break;
                    case 'number':
                        input = document.createElement('input');
                        input.type = 'number';
                        if (config.min !== undefined) input.min = config.min;
                        if (config.max !== undefined) input.max = config.max;
                        if (config.step) input.step = config.step;
                        break;
                    case 'date':
                        input = document.createElement('input');
                        input.type = 'date';
                        break;
                    case 'checkbox':
                        input = document.createElement('input');
                        input.type = 'checkbox';
                        input.className = 'form-check-input';
                        break;
                    default:
                        input = document.createElement('input');
                        input.type = 'text';
                }

                if (fieldType !== 'select' && fieldType !== 'checkbox') {
                    input.className = 'form-control';
                }
                input.name = `attr_${key}`;
                if (config.placeholder) input.placeholder = config.placeholder;
                if (config.required) input.required = true;

                col.appendChild(label);
                col.appendChild(input);
                dynamicFields.appendChild(col);
            }
        })
        .catch(err => {
            console.error('Error loading type schema:', err);
            dynamicSection.style.display = 'none';
        });
    });

    // Trigger on page load if a type is already selected
    if (typeSelect.value) {
        typeSelect.dispatchEvent(new Event('change'));
    }
})();
