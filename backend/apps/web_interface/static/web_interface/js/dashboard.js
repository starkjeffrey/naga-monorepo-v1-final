/**
 * Naga SIS Dashboard JavaScript
 *
 * Main JavaScript functionality for the user-facing web interface.
 * Handles navigation, modals, form interactions, and HTMX integration.
 */

(function() {
    'use strict';

    // Configuration and state
    const DashboardApp = {
        currentUser: null,
        currentRole: null,
        csrfToken: null,

        // Initialize the dashboard
        init() {
            this.loadCSRFToken();
            this.bindEvents();
            this.initializeNavigation();
            this.initializeModals();
            this.initializeHTMX();
        },

        // Load CSRF token from meta tag or cookies
        loadCSRFToken() {
            const token = document.querySelector('meta[name="csrf-token"]');
            if (token) {
                this.csrfToken = token.getAttribute('content');
            } else {
                // Fallback to cookie
                this.csrfToken = this.getCookie('csrftoken');
            }
        },

        // Get cookie value by name
        getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },

        // Bind global event handlers
        bindEvents() {
            // Handle form submissions
            document.addEventListener('submit', this.handleFormSubmit.bind(this));

            // Handle navigation clicks
            document.addEventListener('click', this.handleNavigation.bind(this));

            // Handle modal triggers
            document.addEventListener('click', this.handleModalTrigger.bind(this));

            // Handle language switching
            document.addEventListener('click', this.handleLanguageSwitch.bind(this));

            // Handle mobile menu toggle
            document.addEventListener('click', this.handleMobileMenu.bind(this));

            // Handle search inputs
            document.addEventListener('input', this.handleSearch.bind(this));
        },

        // Initialize navigation functionality
        initializeNavigation() {
            // Set active navigation item based on current URL
            this.updateActiveNavigation();

            // Handle browser back/forward
            window.addEventListener('popstate', this.handlePopState.bind(this));
        },

        // Update active navigation item
        updateActiveNavigation() {
            const currentPath = window.location.pathname;
            const navItems = document.querySelectorAll('.nav-item');

            navItems.forEach(item => {
                const href = item.getAttribute('href');
                if (href && currentPath.includes(href.replace(/\/$/, ''))) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        },

        // Handle navigation clicks
        handleNavigation(event) {
            const navItem = event.target.closest('.nav-item');
            if (!navItem || navItem.getAttribute('href') === '#') {
                return;
            }

            // Update active state
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            navItem.classList.add('active');
        },

        // Handle popstate events (browser back/forward)
        handlePopState(event) {
            this.updateActiveNavigation();
        },

        // Initialize modal functionality
        initializeModals() {
            // Handle modal triggers with HTMX
            document.addEventListener('click', this.handleModalTrigger.bind(this));

            window.closeModal = this.closeModal.bind(this);

            // Handle successful modal form submissions
            document.addEventListener('htmx:afterRequest', (event) => {
                if (event.detail.successful && event.detail.xhr.status === 200) {
                    const response = JSON.parse(event.detail.xhr.responseText || '{}');
                    if (response.success && response.redirect_url) {
                        // Close modal and redirect
                        this.closeModal();
                        if (response.message) {
                            this.showAlert(response.message, 'success');
                        }
                        // Use HTMX to load new content or redirect
                        setTimeout(() => {
                            window.location.href = response.redirect_url;
                        }, 1000);
                    }
                }
            });

            // Handle modal form errors
            document.addEventListener('htmx:responseError', (event) => {
                if (event.detail.xhr.status === 400) {
                    try {
                        const response = JSON.parse(event.detail.xhr.responseText);
                        if (response.form_html) {
                            // Update modal content with form errors
                            const modalBody = document.querySelector('#modal-overlay .modal-body');
                            if (modalBody) {
                                modalBody.innerHTML = response.form_html;
                            }
                        } else if (response.error) {
                            this.showAlert(response.error, 'error');
                        }
                    } catch (e) {
                        console.error('Error parsing response:', e);
                        this.showAlert('An error occurred. Please try again.', 'error');
                    }
                }
            });
        },

        // Show modal with HTMX content
        showModal(content, options = {}) {
            // Remove any existing modals
            this.closeModal();

            // Create modal container in document
            const modalContainer = document.createElement('div');
            modalContainer.id = 'modal-container';
            modalContainer.innerHTML = content;

            document.body.appendChild(modalContainer);
            document.body.classList.add('modal-open');

            // Focus first input after a brief delay
            setTimeout(() => {
                const firstInput = modalContainer.querySelector('input:not([type="hidden"]), select, textarea');
                if (firstInput) {
                    firstInput.focus();
                }
            }, 100);
        },

        closeModal() {
            const modalOverlay = document.getElementById('modal-overlay');
            const modalContainer = document.getElementById('modal-container');

            if (modalOverlay) {
                modalOverlay.remove();
            }
            if (modalContainer) {
                modalContainer.remove();
            }

            document.body.classList.remove('modal-open');
        },

        // Handle modal trigger clicks
        handleModalTrigger(event) {
            const trigger = event.target.closest('[data-modal-url]');
            if (!trigger) return;

            event.preventDefault();

            const url = trigger.getAttribute('data-modal-url');
            const studentId = trigger.getAttribute('data-student-id');
            const invoiceId = trigger.getAttribute('data-invoice-id');

            // Build URL with parameters
            let modalUrl = url;
            const params = new URLSearchParams();

            if (studentId) params.append('student_id', studentId);
            if (invoiceId) params.append('invoice_id', invoiceId);

            if (params.toString()) {
                modalUrl += '?' + params.toString();
            }

            this.loadModalContent(modalUrl);
        },

        // Load modal content via HTMX
        loadModalContent(url) {
            fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'HX-Request': 'true',
                    'X-CSRFToken': this.csrfToken,
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(content => {
                this.showModal(content);
            })
            .catch(error => {
                console.error('Error loading modal content:', error);
                this.showAlert('Error loading content. Please try again.', 'error');
            });
        },

        // Alias for compatibility - openModal calls loadModalContent
        openModal(url) {
            this.loadModalContent(url);
        },

        // Handle quick actions (for buttons that need modal confirmation)
        handleQuickAction(actionType, itemId, itemName) {
            const actions = {
                'delete': {
                    title: 'Confirm Delete',
                    message: `Are you sure you want to delete "${itemName}"? This action cannot be undone.`,
                    confirmText: 'Delete',
                    confirmClass: 'btn-danger'
                },
                'archive': {
                    title: 'Confirm Archive',
                    message: `Are you sure you want to archive "${itemName}"?`,
                    confirmText: 'Archive',
                    confirmClass: 'btn-warning'
                },
                'activate': {
                    title: 'Confirm Activation',
                    message: `Are you sure you want to activate "${itemName}"?`,
                    confirmText: 'Activate',
                    confirmClass: 'btn-success'
                }
            };

            const action = actions[actionType];
            if (!action) return;

            const confirmModal = `
                <div id="modal-overlay" class="modal-overlay" onclick="closeModal()">
                    <div class="modal-container" onclick="event.stopPropagation()">
                        <div class="modal-header">
                            <h3 class="modal-title">${action.title}</h3>
                            <button type="button" class="modal-close-btn" onclick="closeModal()">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p>${action.message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="closeModal()">
                                Cancel
                            </button>
                            <button type="button" class="btn ${action.confirmClass}"
                                    onclick="DashboardApp.executeAction('${actionType}', '${itemId}')">
                                ${action.confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            this.showModal(confirmModal);
        },

        // Execute confirmed action
        executeAction(actionType, itemId) {
            // This would typically make an AJAX request to perform the action
            this.closeModal();
            this.showAlert(`${actionType} action executed for item ${itemId}`, 'success');

            // Reload the current content
            setTimeout(() => {
                location.reload();
            }, 1000);
        },

        // Handle form submissions
        handleFormSubmit(event) {
            const form = event.target;

            // Add CSRF token to forms if not present
            if (this.csrfToken && !form.querySelector('[name="csrfmiddlewaretoken"]')) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = this.csrfToken;
                form.appendChild(csrfInput);
            }

            // Handle HTMX forms differently
            if (form.hasAttribute('hx-post') || form.hasAttribute('hx-put')) {
                return; // Let HTMX handle it
            }

            // Add loading state
            const submitButton = form.querySelector('[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Processing...';
            }
        },

        // Handle language switching
        handleLanguageSwitch(event) {
            const langBtn = event.target.closest('.lang-btn');
            if (!langBtn) return;

            event.preventDefault();

            // Update active language button
            document.querySelectorAll('.lang-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            langBtn.classList.add('active');

            // TODO: Implement actual language switching
            const language = langBtn.textContent.includes('English') ? 'en' : 'km';
            this.switchLanguage(language);
        },

        // Switch language
        switchLanguage(language) {
            // This would typically make an AJAX request to change the language
            // For now, we'll just store it in localStorage
            localStorage.setItem('preferred_language', language);

            // In a real implementation, you would reload content or update text
            console.log(`Language switched to: ${language}`);
        },

        // Handle mobile menu toggle
        handleMobileMenu(event) {
            const menuToggle = event.target.closest('.mobile-menu-toggle');
            if (!menuToggle) return;

            event.preventDefault();
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                sidebar.classList.toggle('open');
            }
        },

        // Handle search inputs
        handleSearch(event) {
            const searchInput = event.target.closest('[data-search]');
            if (!searchInput) return;

            const searchType = searchInput.getAttribute('data-search');
            const query = searchInput.value.trim();

            // Debounce search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.performSearch(searchType, query);
            }, 300);
        },

        // Perform search via HTMX/AJAX
        performSearch(searchType, query) {
            if (query.length < 2) return;

            const url = `/web/htmx/search/${searchType}/`;

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                this.updateSearchResults(searchType, data.results);
            })
            .catch(error => {
                console.error('Search error:', error);
            });
        },

        // Update search results
        updateSearchResults(searchType, results) {
            const resultsContainer = document.querySelector(`[data-search-results="${searchType}"]`);
            if (!resultsContainer) return;

            resultsContainer.innerHTML = results;
        },

        // Initialize HTMX specific functionality
        initializeHTMX() {
            // Add CSRF token to all HTMX requests
            document.addEventListener('htmx:configRequest', (event) => {
                event.detail.headers['X-CSRFToken'] = this.csrfToken;
            });

            // Handle HTMX errors
            document.addEventListener('htmx:responseError', (event) => {
                console.error('HTMX Error:', event.detail);
                this.showAlert('An error occurred. Please try again.', 'error');
            });

            // Handle successful HTMX requests
            document.addEventListener('htmx:afterRequest', (event) => {
                if (event.detail.successful) {
                    // Re-bind any new elements
                    this.bindDynamicElements();
                }
            });
        },

        // Bind events to dynamically loaded elements
        bindDynamicElements() {
            // Re-initialize any JavaScript components in newly loaded content
            this.initializeTabs();
            this.initializePagination();
            this.initializeTooltips();
        },

        // Initialize tab functionality
        initializeTabs() {
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', (event) => {
                    event.preventDefault();

                    const targetContent = tab.getAttribute('data-tab-content');
                    if (!targetContent) return;

                    // Update active tab
                    tab.closest('.tabs').querySelectorAll('.tab').forEach(t => {
                        t.classList.remove('active');
                    });
                    tab.classList.add('active');

                    // Show content
                    document.querySelectorAll('[data-tab-panel]').forEach(panel => {
                        panel.classList.add('d-none');
                    });

                    const targetPanel = document.querySelector(`[data-tab-panel="${targetContent}"]`);
                    if (targetPanel) {
                        targetPanel.classList.remove('d-none');
                    }
                });
            });
        },

        // Initialize pagination
        initializePagination() {
            document.querySelectorAll('[data-page]').forEach(pageLink => {
                pageLink.addEventListener('click', (event) => {
                    event.preventDefault();

                    const page = pageLink.getAttribute('data-page');
                    const target = pageLink.getAttribute('data-target');

                    if (target) {
                        // Use HTMX for pagination
                        const targetElement = document.querySelector(target);
                        if (targetElement) {
                            targetElement.setAttribute('hx-get', `${window.location.pathname}?page=${page}`);
                            htmx.trigger(targetElement, 'htmx:trigger');
                        }
                    }
                });
            });
        },

        // Initialize tooltips
        initializeTooltips() {
            // Simple tooltip implementation
            document.querySelectorAll('[data-tooltip]').forEach(element => {
                element.addEventListener('mouseenter', this.showTooltip);
                element.addEventListener('mouseleave', this.hideTooltip);
            });
        },

        // Show tooltip
        showTooltip(event) {
            const element = event.target;
            const tooltipText = element.getAttribute('data-tooltip');

            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = tooltipText;
            tooltip.style.position = 'absolute';
            tooltip.style.background = '#333';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '12px';
            tooltip.style.zIndex = '9999';
            tooltip.style.pointerEvents = 'none';

            document.body.appendChild(tooltip);

            const rect = element.getBoundingClientRect();
            tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;

            element._tooltip = tooltip;
        },

        // Hide tooltip
        hideTooltip(event) {
            const element = event.target;
            if (element._tooltip) {
                document.body.removeChild(element._tooltip);
                delete element._tooltip;
            }
        },

        // Show alert message
        showAlert(message, type = 'info') {
            const alertContainer = document.getElementById('alerts') || this.createAlertContainer();

            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.innerHTML = `
                <span>${message}</span>
                <button type="button" class="alert-close">&times;</button>
            `;

            alertContainer.appendChild(alert);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (alert.parentNode) {
                    alertContainer.removeChild(alert);
                }
            }, 5000);

            alert.querySelector('.alert-close').addEventListener('click', () => {
                if (alert.parentNode) {
                    alertContainer.removeChild(alert);
                }
            });
        },

        // Create alert container if it doesn't exist
        createAlertContainer() {
            const container = document.createElement('div');
            container.id = 'alerts';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
            return container;
        },

        // Format currency
        formatCurrency(amount, currency = 'USD') {
            if (currency === 'USD') {
                return `$${parseFloat(amount).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            } else if (currency === 'KHR') {
                return `៛${parseFloat(amount).toLocaleString('en-US', {maximumFractionDigits: 0})}`;
            }
            return `${currency} ${parseFloat(amount).toFixed(2)}`;
        },

        // Utility function to format dates
        formatDate(dateString, options = {}) {
            const date = new Date(dateString);
            const defaultOptions = {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            };
            return date.toLocaleDateString('en-US', {...defaultOptions, ...options});
        }
    };

    // Login form functionality (for login page)
    function initializeLogin() {
        const loginForm = document.getElementById('loginForm');
        if (!loginForm) return;

        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();

            const formData = new FormData(loginForm);
            const submitButton = loginForm.querySelector('[type="submit"]');

            // Show loading state
            submitButton.disabled = true;
            submitButton.textContent = 'Signing in...';

            fetch(loginForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect_url || '/web/dashboard/';
                } else {
                    DashboardApp.showAlert(data.error || 'Login failed. Please try again.', 'error');
                    submitButton.disabled = false;
                    submitButton.textContent = 'Sign In';
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                DashboardApp.showAlert('An error occurred. Please try again.', 'error');
                submitButton.disabled = false;
                submitButton.textContent = 'Sign In';
            });
        });
    }

    // Initialize everything when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        DashboardApp.init();
        initializeLogin();
    });

    // Make DashboardApp globally available
    window.DashboardApp = DashboardApp;

})();
