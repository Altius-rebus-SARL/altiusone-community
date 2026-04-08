/**
 * Translated Fields — Gestion des onglets multilingues
 *
 * Fonctionnalites:
 * - Indicateur visuel (point vert) sur les onglets dont le champ est rempli
 * - Initialisation automatique des tooltips Bootstrap sur les icones d'aide
 * - Compatible HTMX (reinitialise apres swap)
 */
(function () {
  "use strict";

  /**
   * Met a jour l'indicateur "filled" sur les onglets traduits.
   * Un point vert apparait sur l'onglet quand le champ contient du texte.
   */
  function updateFilledIndicators(group) {
    const panes = group.querySelectorAll(".tab-pane");
    panes.forEach(function (pane) {
      const input =
        pane.querySelector("input") || pane.querySelector("textarea");
      if (!input) return;

      const lang = pane.id.split("-").pop();
      const fieldName = group.dataset.field;
      const tab = group.querySelector("#tab-" + fieldName + "-" + lang);
      if (!tab) return;

      function update() {
        tab.setAttribute(
          "data-filled",
          input.value.trim().length > 0 ? "true" : "false"
        );
      }

      update();
      input.addEventListener("input", update);
    });
  }

  /**
   * Initialise tous les groupes de champs traduits dans le scope donne.
   */
  function initTranslatedFields(scope) {
    var root = scope || document;
    var groups = root.querySelectorAll(".translated-field-group");
    groups.forEach(updateFilledIndicators);

    // Initialiser les tooltips Bootstrap sur les icones d'aide
    var tooltips = root.querySelectorAll(".translated-field-help[data-bs-toggle='tooltip']");
    tooltips.forEach(function (el) {
      // Eviter la double-init
      if (!bootstrap.Tooltip.getInstance(el)) {
        new bootstrap.Tooltip(el);
      }
    });
  }

  // Init au chargement
  document.addEventListener("DOMContentLoaded", function () {
    initTranslatedFields(document);
  });

  // Re-init apres swap HTMX
  document.addEventListener("htmx:afterSwap", function (evt) {
    initTranslatedFields(evt.detail.target);
  });

  // Exposer pour usage manuel si besoin
  window.initTranslatedFields = initTranslatedFields;
})();
