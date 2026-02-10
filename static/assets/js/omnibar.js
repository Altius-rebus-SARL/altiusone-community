/**
 * Omnibar - Recherche globale en temps réel (style Spotlight/Notion)
 *
 * Debounce 300ms, AJAX GET, rendu groupé, navigation clavier, XSS-safe.
 */
(function ($) {
  "use strict";

  // --- Helpers -----------------------------------------------------------

  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function highlightTerm(text, term) {
    if (!text || !term) return escapeHtml(text);
    var safe = escapeHtml(text);
    var escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var re = new RegExp("(" + escaped + ")", "gi");
    return safe.replace(re, "<mark>$1</mark>");
  }

  var COLOR_MAP = {
    primary: { bg: "bg-light-primary", text: "text-primary" },
    success: { bg: "bg-light-success", text: "text-success" },
    danger: { bg: "bg-light-danger", text: "text-danger" },
    warning: { bg: "bg-light-warning", text: "text-warning" },
    info: { bg: "bg-light-info", text: "text-info" },
    dark: { bg: "bg-light-dark", text: "text-dark" },
    secondary: { bg: "bg-light-secondary", text: "text-secondary" },
  };

  function colorClasses(color) {
    return COLOR_MAP[color] || COLOR_MAP.secondary;
  }

  // --- State -------------------------------------------------------------

  var $input, $dropdown, $results, $footer, $spinner, $icon, $form;
  var searchUrl, fullUrl;
  var debounceTimer = null;
  var currentXhr = null;
  var activeIndex = -1;
  var lastQuery = "";
  var lastData = null;

  // --- Rendering ---------------------------------------------------------

  function renderResults(data, query) {
    lastData = data;
    $results.empty();
    activeIndex = -1;

    var groups = data.groups || {};
    var keys = Object.keys(groups);

    if (!keys.length) {
      $results.html(
        '<div class="omnibar-empty">' +
          '<i class="ph ph-magnifying-glass f-s-30 text-muted mb-2"></i>' +
          '<span class="text-muted f-s-13">Aucun résultat pour «\u00a0' +
          escapeHtml(query) +
          "\u00a0»</span></div>"
      );
      $footer.addClass("d-none");
      $dropdown.removeClass("d-none");
      return;
    }

    var totalRendered = 0;
    var MAX_ITEMS = 8;

    for (var i = 0; i < keys.length && totalRendered < MAX_ITEMS; i++) {
      var key = keys[i];
      var group = groups[key];
      var cc = colorClasses(group.color);

      var headerHtml =
        '<div class="omnibar-group-header">' +
        '<i class="' +
        escapeHtml(group.icon) +
        " me-1 " +
        cc.text +
        '"></i>' +
        '<span>' +
        escapeHtml(group.label) +
        "</span></div>";
      $results.append(headerHtml);

      var items = group.results || [];
      for (var j = 0; j < items.length && totalRendered < MAX_ITEMS; j++) {
        var item = items[j];
        var itemCc = colorClasses(item.color || group.color);
        var itemHtml =
          '<a href="' +
          escapeHtml(item.url) +
          '" class="omnibar-item" data-index="' +
          totalRendered +
          '">' +
          '<span class="omnibar-item-icon ' +
          itemCc.bg +
          " " +
          itemCc.text +
          '">' +
          '<i class="' +
          escapeHtml(item.icon || group.icon) +
          '"></i></span>' +
          '<span class="omnibar-item-text">' +
          '<span class="omnibar-item-title">' +
          highlightTerm(item.title, query) +
          "</span>" +
          '<span class="omnibar-item-subtitle">' +
          escapeHtml(item.subtitle) +
          "</span></span></a>";
        $results.append(itemHtml);
        totalRendered++;
      }
    }

    // Footer
    if (data.total > totalRendered) {
      $footer
        .attr("href", fullUrl + "?q=" + encodeURIComponent(query))
        .find("span")
        .text("Voir les " + data.total + " résultats");
      $footer.removeClass("d-none");
    } else {
      $footer.addClass("d-none");
    }

    $dropdown.removeClass("d-none");
  }

  // --- AJAX --------------------------------------------------------------

  function doSearch(query) {
    if (currentXhr) {
      currentXhr.abort();
      currentXhr = null;
    }

    $spinner.removeClass("d-none");
    $icon.addClass("d-none");

    currentXhr = $.ajax({
      url: searchUrl,
      data: { q: query },
      dataType: "json",
      success: function (data) {
        renderResults(data, query);
      },
      error: function (xhr) {
        if (xhr.statusText !== "abort") {
          $dropdown.addClass("d-none");
        }
      },
      complete: function () {
        $spinner.addClass("d-none");
        $icon.removeClass("d-none");
        currentXhr = null;
      },
    });
  }

  // --- Keyboard ----------------------------------------------------------

  function getVisibleItems() {
    return $results.find(".omnibar-item");
  }

  function setActive(index) {
    var $items = getVisibleItems();
    $items.removeClass("active");
    activeIndex = index;
    if (index >= 0 && index < $items.length) {
      $items.eq(index).addClass("active");
      // Scroll into view
      var el = $items[index];
      if (el) {
        el.scrollIntoView({ block: "nearest" });
      }
    }
  }

  function handleKeydown(e) {
    if ($dropdown.hasClass("d-none")) return;

    var $items = getVisibleItems();
    var count = $items.length;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(activeIndex < count - 1 ? activeIndex + 1 : 0);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(activeIndex > 0 ? activeIndex - 1 : count - 1);
    } else if (e.key === "Enter") {
      if (activeIndex >= 0 && activeIndex < count) {
        e.preventDefault();
        var href = $items.eq(activeIndex).attr("href");
        if (href) window.location.href = href;
      }
      // else: let form submit normally (full-page search)
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeDropdown();
      $input.blur();
    }
  }

  // --- Open / Close ------------------------------------------------------

  function closeDropdown() {
    $dropdown.addClass("d-none");
    activeIndex = -1;
  }

  // --- Init --------------------------------------------------------------

  $(function () {
    $input = $("#omnibar-input");
    if (!$input.length) return;

    $form = $("#omnibar-form");
    $dropdown = $("#omnibar-dropdown");
    $results = $("#omnibar-results");
    $footer = $("#omnibar-footer");
    $spinner = $("#omnibar-spinner");
    $icon = $("#omnibar-icon");

    searchUrl = $input.data("search-url");
    fullUrl = $input.data("full-url");

    if (!searchUrl) return;

    // Input -> debounce search
    $input.on("input", function () {
      var q = $.trim($input.val());
      lastQuery = q;
      clearTimeout(debounceTimer);

      if (q.length < 2) {
        closeDropdown();
        if (currentXhr) {
          currentXhr.abort();
          currentXhr = null;
        }
        $spinner.addClass("d-none");
        $icon.removeClass("d-none");
        return;
      }

      debounceTimer = setTimeout(function () {
        doSearch(q);
      }, 300);
    });

    // Keyboard nav
    $input.on("keydown", handleKeydown);

    // Click outside closes dropdown
    $(document).on("mousedown", function (e) {
      if (
        !$(e.target).closest("#omnibar-dropdown, #omnibar-input").length
      ) {
        closeDropdown();
      }
    });

    // Focus re-opens if data exists
    $input.on("focus", function () {
      if (lastData && $.trim($input.val()).length >= 2) {
        $dropdown.removeClass("d-none");
      }
    });

    // Hover on items
    $dropdown.on("mouseenter", ".omnibar-item", function () {
      var idx = parseInt($(this).data("index"), 10);
      setActive(idx);
    });

    // Click on items - explicit handler for reliable navigation
    $dropdown.on("click", ".omnibar-item", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var href = $(this).attr("href");
      if (href) window.location.href = href;
    });

    // Click on footer
    $dropdown.on("click", ".omnibar-footer", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var href = $(this).attr("href");
      if (href) window.location.href = href;
    });

    // Form submit prevention when dropdown item selected
    $form.on("submit", function (e) {
      var $items = getVisibleItems();
      if (activeIndex >= 0 && activeIndex < $items.length) {
        e.preventDefault();
        var href = $items.eq(activeIndex).attr("href");
        if (href) window.location.href = href;
      }
    });

    // Keyboard shortcut: Ctrl+K or / to focus
    $(document).on("keydown", function (e) {
      if (
        (e.ctrlKey && e.key === "k") ||
        (e.key === "/" &&
          !$(e.target).is("input, textarea, select, [contenteditable]"))
      ) {
        e.preventDefault();
        $input.focus().select();
      }
    });
  });
})(jQuery);
