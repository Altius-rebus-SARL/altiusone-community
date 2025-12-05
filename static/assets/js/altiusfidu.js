// static/assets/js/altiusfidu.js

(function() {
    'use strict';

    // ========================================
    // SIDEBAR ACTIVE STATE MANAGEMENT
    // ========================================
    
    function initSidebarActiveState() {
        const currentPath = window.location.pathname;
        const menuLinks = document.querySelectorAll('.main-nav a[href]');
        
        // Reset all active states
        document.querySelectorAll('.main-nav li').forEach(li => {
            li.classList.remove('active');
        });
        document.querySelectorAll('.main-nav .collapse').forEach(collapse => {
            collapse.classList.remove('show');
        });
        document.querySelectorAll('.main-nav a[aria-expanded]').forEach(a => {
            a.setAttribute('aria-expanded', 'false');
        });

        // Find and activate the matching link
        menuLinks.forEach(link => {
            const href = link.getAttribute('href');
            
            // Skip collapse toggles and empty hrefs
            if (!href || href === '#' || href.startsWith('#')) return;
            
            // Check if current path matches or starts with the link href
            if (currentPath === href || currentPath.startsWith(href)) {
                // Activate the link's parent li
                const parentLi = link.closest('li');
                if (parentLi) {
                    parentLi.classList.add('active');
                }
                
                // If it's a submenu item, also expand the parent menu
                const parentCollapse = link.closest('.collapse');
                if (parentCollapse) {
                    parentCollapse.classList.add('show');
                    
                    // Find and activate the parent menu item
                    const parentMenu = parentCollapse.closest('li');
                    if (parentMenu) {
                        parentMenu.classList.add('active');
                        
                        // Update aria-expanded on the toggle
                        const toggle = parentMenu.querySelector('a[data-bs-toggle="collapse"]');
                        if (toggle) {
                            toggle.setAttribute('aria-expanded', 'true');
                        }
                    }
                }
            }
        });
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