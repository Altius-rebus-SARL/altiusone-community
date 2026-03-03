// static/assets/js/altiusone.js

(function() {
    'use strict';

    // ========================================
    // SIDEBAR ACTIVE STATE MANAGEMENT
    // Uses data-active attributes from Django templates
    // ========================================

    function initSidebarActiveState() {
        const mainNav = document.querySelector('.main-nav');
        if (!mainNav) return;

        // First, handle data-active="true" attributes set by Django
        const activeItems = mainNav.querySelectorAll('li[data-active="true"]');

        activeItems.forEach(item => {
            item.classList.add('active');

            // If it's a submenu item, expand the parent collapse
            const parentCollapse = item.closest('ul.collapse');
            if (parentCollapse) {
                parentCollapse.classList.add('show');

                // Find the parent li and its toggle
                const parentLi = parentCollapse.closest('li');
                if (parentLi) {
                    parentLi.classList.add('active');
                    const toggle = parentLi.querySelector(':scope > a[data-bs-toggle="collapse"]');
                    if (toggle) {
                        toggle.setAttribute('aria-expanded', 'true');
                    }
                }
            }
        });

        // Handle data-show="true" on collapse elements
        const showCollapses = mainNav.querySelectorAll('ul.collapse[data-show="true"]');
        showCollapses.forEach(collapse => {
            collapse.classList.add('show');
            const parentLi = collapse.closest('li');
            if (parentLi) {
                const toggle = parentLi.querySelector(':scope > a[data-bs-toggle="collapse"]');
                if (toggle) {
                    toggle.setAttribute('aria-expanded', 'true');
                }
            }
        });

        // Fallback: if no data-active found, use URL matching
        if (activeItems.length === 0) {
            const currentPath = window.location.pathname;
            const menuLinks = mainNav.querySelectorAll('a[href]');

            menuLinks.forEach(link => {
                const href = link.getAttribute('href');

                // Skip collapse toggles and empty hrefs
                if (!href || href === '#' || href.startsWith('#')) return;

                // Check if current path matches or starts with the link href
                // But href must be more than just the language prefix
                if (href.length > 4 && (currentPath === href || currentPath.startsWith(href))) {
                    const parentLi = link.closest('li');
                    if (parentLi && !parentLi.classList.contains('menu-title')) {
                        parentLi.classList.add('active');

                        // Expand parent collapse if exists
                        const parentCollapse = link.closest('.collapse');
                        if (parentCollapse) {
                            parentCollapse.classList.add('show');

                            const parentMenu = parentCollapse.closest('li');
                            if (parentMenu) {
                                parentMenu.classList.add('active');
                                const toggle = parentMenu.querySelector(':scope > a[data-bs-toggle="collapse"]');
                                if (toggle) {
                                    toggle.setAttribute('aria-expanded', 'true');
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebarActiveState);
    } else {
        initSidebarActiveState();
    }

    // Also run after HTMX content swaps (if using HTMX)
    document.body.addEventListener('htmx:afterSettle', initSidebarActiveState);

})();
