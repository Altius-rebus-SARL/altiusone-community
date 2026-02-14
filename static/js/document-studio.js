/**
 * Document Studio — Module JS reutilisable pour l'editeur 2 panneaux PDF.
 *
 * Usage:
 *   DocumentStudio.init({
 *       previewUrl:    '/facturation/api/studio/preview/',
 *       typeDocument:  'FACTURE',
 *       instanceId:    '<uuid>',
 *       csrfToken:     '{{ csrf_token }}',
 *       initialConfig: { ... },  // config JSON du ModeleDocumentPDF
 *   });
 */
var DocumentStudio = (function() {
    'use strict';

    // =========================================================================
    // STATE
    // =========================================================================
    var _config = {};
    var _previewTimer = null;
    var _previewRequestId = 0;
    var _currentZoom = 100;
    var _DEBOUNCE_MS = 800;

    // =========================================================================
    // INIT
    // =========================================================================
    function init(options) {
        _config = {
            previewUrl:    options.previewUrl,
            typeDocument:  options.typeDocument,
            instanceId:    options.instanceId,
            csrfToken:     options.csrfToken,
            initialConfig: options.initialConfig || {},
            saveUrl:       options.saveUrl || null,
            loadUrl:       options.loadUrl || null,
        };

        _bindConfigInputs();
        _bindZoomControls();
        _bindActionButtons();
        _initColorPickers();

        // Preview initiale
        _debouncePreview();
    }

    // =========================================================================
    // CONFIG COLLECTION
    // =========================================================================
    function collectConfig() {
        var config = {};

        // Instance ID
        config.instance_id = _config.instanceId;

        // Couleurs
        var fields = document.querySelectorAll('[data-studio-field]');
        fields.forEach(function(el) {
            var field = el.getAttribute('data-studio-field');
            var type = el.getAttribute('data-studio-type') || 'string';

            if (el.type === 'checkbox') {
                _setNestedValue(config, field, el.checked);
            } else if (type === 'number') {
                _setNestedValue(config, field, parseInt(el.value, 10) || 0);
            } else {
                _setNestedValue(config, field, el.value);
            }
        });

        // Blocs visibles (toggles)
        var toggles = document.querySelectorAll('[data-studio-bloc]');
        if (!config.blocs_visibles) config.blocs_visibles = {};
        toggles.forEach(function(el) {
            var bloc = el.getAttribute('data-studio-bloc');
            config.blocs_visibles[bloc] = el.checked;
        });

        // Textes
        var textes = document.querySelectorAll('[data-studio-texte]');
        if (!config.textes) config.textes = {};
        textes.forEach(function(el) {
            var key = el.getAttribute('data-studio-texte');
            config.textes[key] = el.value;
        });

        return config;
    }

    // =========================================================================
    // PREVIEW
    // =========================================================================
    function _debouncePreview() {
        clearTimeout(_previewTimer);
        _previewTimer = setTimeout(_refreshPreview, _DEBOUNCE_MS);
    }

    function _refreshPreview() {
        var config = collectConfig();

        // Show loading
        _showState('loading');

        _previewRequestId++;
        var thisRequestId = _previewRequestId;

        fetch(_config.previewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': _config.csrfToken,
            },
            body: JSON.stringify(config),
        })
        .then(function(response) {
            if (thisRequestId !== _previewRequestId) return null;
            if (!response.ok) {
                return response.json().then(function(data) {
                    throw new Error(data.error || 'Erreur serveur');
                });
            }
            return response.blob();
        })
        .then(function(blob) {
            if (!blob || thisRequestId !== _previewRequestId) return;

            var pdfUrl = URL.createObjectURL(blob);
            var iframe = document.getElementById('studio-pdf-preview');
            if (iframe) {
                iframe.src = pdfUrl;
            }
            _showState('preview');
        })
        .catch(function(error) {
            if (thisRequestId !== _previewRequestId) return;
            console.error('Studio preview error:', error);
            _showState('error', error.message);
        });
    }

    function _showState(state, message) {
        var loading = document.getElementById('studio-preview-loading');
        var empty = document.getElementById('studio-preview-empty');
        var iframe = document.getElementById('studio-pdf-preview');
        var errorEl = document.getElementById('studio-preview-error');

        if (loading) loading.style.display = state === 'loading' ? 'flex' : 'none';
        if (empty) empty.style.display = state === 'empty' ? 'flex' : 'none';
        if (iframe) iframe.style.display = state === 'preview' ? 'block' : 'none';
        if (errorEl) {
            errorEl.style.display = state === 'error' ? 'flex' : 'none';
            if (state === 'error') {
                var msgEl = errorEl.querySelector('.error-message');
                if (msgEl) msgEl.textContent = message || 'Erreur inconnue';
            }
        }
    }

    // =========================================================================
    // BINDINGS
    // =========================================================================
    function _bindConfigInputs() {
        // Tous les champs data-studio-field
        document.querySelectorAll('[data-studio-field]').forEach(function(el) {
            var event = (el.type === 'color' || el.type === 'checkbox') ? 'change' : 'input';
            el.addEventListener(event, _debouncePreview);
        });

        // Blocs visibles
        document.querySelectorAll('[data-studio-bloc]').forEach(function(el) {
            el.addEventListener('change', _debouncePreview);
        });

        // Textes
        document.querySelectorAll('[data-studio-texte]').forEach(function(el) {
            el.addEventListener('input', _debouncePreview);
        });
    }

    function _bindZoomControls() {
        var zoomIn = document.getElementById('studio-zoom-in');
        var zoomOut = document.getElementById('studio-zoom-out');

        if (zoomIn) {
            zoomIn.addEventListener('click', function() { _changeZoom(10); });
        }
        if (zoomOut) {
            zoomOut.addEventListener('click', function() { _changeZoom(-10); });
        }

        var refreshBtn = document.getElementById('studio-refresh-preview');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', _refreshPreview);
        }
    }

    function _changeZoom(delta) {
        _currentZoom = Math.max(50, Math.min(200, _currentZoom + delta));
        var levelEl = document.getElementById('studio-zoom-level');
        if (levelEl) levelEl.textContent = _currentZoom + '%';

        var iframe = document.getElementById('studio-pdf-preview');
        if (iframe) {
            iframe.style.transform = 'scale(' + (_currentZoom / 100) + ')';
            iframe.style.transformOrigin = 'top center';
        }
    }

    function _bindActionButtons() {
        // Sauvegarder le modele
        var saveBtn = document.getElementById('studio-save-model');
        if (saveBtn) {
            saveBtn.addEventListener('click', _saveModel);
        }
    }

    function _initColorPickers() {
        // Synchroniser les color inputs avec les text inputs
        document.querySelectorAll('.studio-color-group').forEach(function(group) {
            var colorInput = group.querySelector('input[type="color"]');
            var textInput = group.querySelector('input[type="text"]');
            if (colorInput && textInput) {
                colorInput.addEventListener('input', function() {
                    textInput.value = colorInput.value;
                });
                textInput.addEventListener('input', function() {
                    if (/^#[0-9a-fA-F]{6}$/.test(textInput.value)) {
                        colorInput.value = textInput.value;
                    }
                });
            }
        });
    }

    // =========================================================================
    // SAVE MODEL
    // =========================================================================
    function _saveModel() {
        if (!_config.saveUrl) {
            console.warn('No saveUrl configured');
            return;
        }

        var config = collectConfig();
        var saveBtn = document.getElementById('studio-save-model');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Sauvegarde...';
        }

        fetch(_config.saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': _config.csrfToken,
            },
            body: JSON.stringify({
                type_document: _config.typeDocument,
                config: config,
            }),
        })
        .then(function(response) {
            if (!response.ok) throw new Error('Erreur sauvegarde');
            return response.json();
        })
        .then(function(data) {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="ph-duotone ph-floppy-disk me-1"></i> Sauvegardé';
                setTimeout(function() {
                    saveBtn.innerHTML = '<i class="ph-duotone ph-floppy-disk me-1"></i> Sauvegarder le modèle';
                }, 2000);
            }
        })
        .catch(function(error) {
            console.error('Save error:', error);
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="ph-duotone ph-floppy-disk me-1"></i> Sauvegarder le modèle';
            }
            alert('Erreur lors de la sauvegarde du modèle');
        });
    }

    // =========================================================================
    // HELPERS
    // =========================================================================
    function _setNestedValue(obj, path, value) {
        var keys = path.split('.');
        var current = obj;
        for (var i = 0; i < keys.length - 1; i++) {
            if (!current[keys[i]]) current[keys[i]] = {};
            current = current[keys[i]];
        }
        current[keys[keys.length - 1]] = value;
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================
    return {
        init: init,
        collectConfig: collectConfig,
        refreshPreview: _refreshPreview,
    };
})();
