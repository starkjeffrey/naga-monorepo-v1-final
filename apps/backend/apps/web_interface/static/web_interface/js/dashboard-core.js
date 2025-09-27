/**
 * Dashboard Core - Minimal, optimized JavaScript for Naga SIS
 * Focus: Performance, simplicity, sub-second response times
 */

(function() {
    'use strict';

    // Cache DOM queries
    const cache = new Map();
    
    function $(selector) {
        if (!cache.has(selector)) {
            cache.set(selector, document.querySelector(selector));
        }
        return cache.get(selector);
    }

    // Minimal Dashboard App
    window.DashboardApp = {
        // Simple alert system
        showAlert: function(message, type = 'info') {
            const alertsContainer = $('#alerts');
            if (!alertsContainer) return;

            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            
            alertsContainer.appendChild(alert);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        },

        // Simple modal system
        openModal: function(url) {
            const modal = $('#modal');
            if (!modal || !url) return;
            
            modal.style.display = 'block';
            
            // Use HTMX if available, otherwise fetch
            if (window.htmx) {
                htmx.ajax('GET', url, {target: '#modalBody'});
            } else {
                fetch(url)
                    .then(response => response.text())
                    .then(html => {
                        $('#modalBody').innerHTML = html;
                    });
            }
        },

        closeModal: function() {
            const modal = $('#modal');
            if (modal) {
                modal.style.display = 'none';
                $('#modalBody').innerHTML = '';
            }
        },

        // Simplified table search (no complex filtering)
        searchTable: function(inputId, tableId) {
            const input = $(inputId);
            const table = $(tableId);
            
            if (!input || !table) return;
            
            const filter = input.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        }
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        // Handle modal triggers
        document.addEventListener('click', function(e) {
            const modalTrigger = e.target.closest('[data-modal-url]');
            if (modalTrigger) {
                e.preventDefault();
                DashboardApp.openModal(modalTrigger.dataset.modalUrl);
            }
        });

        // Handle modal close
        document.addEventListener('click', function(e) {
            if (e.target.matches('.btn-close, .modal-close')) {
                DashboardApp.closeModal();
            }
        });

        // Close modal on outside click
        const modal = $('#modal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    DashboardApp.closeModal();
                }
            });
        }

        // Simple table search initialization
        const searchInput = $('#tableSearch');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    DashboardApp.searchTable('#tableSearch', '#dataTable');
                }, 300);
            });
        }

        // Add bindDynamicElements method
        DashboardApp.bindDynamicElements = function() {
            // Re-initialize event listeners for dynamically loaded content
            // This function is called after HTMX swaps content
            console.log('Binding dynamic elements...');
        };

        // HTMX enhancements
        if (window.htmx) {
            // Show loading indicator
            document.body.addEventListener('htmx:beforeRequest', function(e) {
                const target = e.target;
                if (target.dataset.loadingText) {
                    target.textContent = target.dataset.loadingText;
                    target.disabled = true;
                }
            });

            // Hide loading indicator
            document.body.addEventListener('htmx:afterRequest', function(e) {
                const target = e.target;
                if (target.dataset.originalText) {
                    target.textContent = target.dataset.originalText;
                    target.disabled = false;
                }
            });

            // Handle HTMX errors gracefully
            document.body.addEventListener('htmx:responseError', function(e) {
                DashboardApp.showAlert('An error occurred. Please try again.', 'error');
            });
        }
    });

    // Performance monitoring (optional, remove in production)
    if (window.performance && window.performance.timing) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const timing = window.performance.timing;
                const loadTime = timing.loadEventEnd - timing.navigationStart;
                console.log('Page load time:', loadTime + 'ms');
                
                if (loadTime > 1000) {
                    console.warn('Page load exceeded 1 second target');
                }
            }, 0);
        });
    }
})();