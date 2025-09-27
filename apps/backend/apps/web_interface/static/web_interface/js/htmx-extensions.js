/**
 * HTMX Extensions for Naga SIS Dashboard
 *
 * Custom HTMX functionality and extensions specific to the Naga SIS interface.
 * Handles modal loading, form submissions, and dynamic content updates.
 */

(function() {
    'use strict';

    // HTMX Modal Extension
    htmx.defineExtension('naga-modal', {
        onEvent: function(name, evt) {
            if (name === 'htmx:afterRequest') {
                const xhr = evt.detail.xhr;
                const target = evt.detail.target;

                // Handle modal responses
                if (target.closest('.modal') && xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success && response.close_modal) {
                            window.DashboardApp.closeModal();
                            if (response.message) {
                                window.DashboardApp.showAlert(response.message, 'success');
                            }
                            // Refresh the page content if needed
                            if (response.refresh_target) {
                                const refreshTarget = document.querySelector(response.refresh_target);
                                if (refreshTarget && refreshTarget.hasAttribute('hx-get')) {
                                    htmx.trigger(refreshTarget, 'htmx:trigger');
                                }
                            }
                        }
                    } catch (e) {
                        // Response is HTML, not JSON - just update the modal content
                    }
                }
            }
        }
    });

    // HTMX Form Extension
    htmx.defineExtension('naga-forms', {
        onEvent: function(name, evt) {
            if (name === 'htmx:beforeRequest') {
                const form = evt.detail.elt;
                if (form.tagName === 'FORM') {
                    // Add loading state to submit button
                    const submitButton = form.querySelector('[type="submit"]');
                    if (submitButton) {
                        submitButton.disabled = true;
                        submitButton.dataset.originalText = submitButton.textContent;
                        submitButton.textContent = 'Processing...';
                    }
                }
            } else if (name === 'htmx:afterRequest') {
                const form = evt.detail.elt;
                if (form.tagName === 'FORM') {
                    // Restore submit button
                    const submitButton = form.querySelector('[type="submit"]');
                    if (submitButton) {
                        submitButton.disabled = false;
                        if (submitButton.dataset.originalText) {
                            submitButton.textContent = submitButton.dataset.originalText;
                            delete submitButton.dataset.originalText;
                        }
                    }
                }

                // Handle form validation errors
                const xhr = evt.detail.xhr;
                if (xhr.status === 400) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.form_errors) {
                            this.displayFormErrors(form, response.form_errors);
                        }
                    } catch (e) {
                        // Response is HTML - HTMX will handle it normally
                    }
                }

                // Handle successful login with redirect
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success && response.redirect_url) {
                            // Redirect to the specified URL
                            window.location.href = response.redirect_url;
                            return;
                        }
                    } catch (e) {
                        // Response is HTML - let HTMX handle it normally
                    }
                }
            }
        },

        displayFormErrors: function(form, errors) {
            // Clear existing errors
            form.querySelectorAll('.field-error').forEach(error => error.remove());
            form.querySelectorAll('.is-invalid').forEach(field => field.classList.remove('is-invalid'));

            // Display new errors
            for (const [fieldName, fieldErrors] of Object.entries(errors)) {
                const field = form.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    field.classList.add('is-invalid');

                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'field-error text-danger mt-1';
                    errorDiv.innerHTML = fieldErrors.join('<br>');

                    field.parentNode.appendChild(errorDiv);
                }
            }
        }
    });

    // HTMX Search Extension
    htmx.defineExtension('naga-search', {
        onEvent: function(name, evt) {
            if (name === 'htmx:beforeRequest') {
                const element = evt.detail.elt;
                if (element.hasAttribute('hx-search')) {
                    const query = element.value.trim();
                    if (query.length < 2) {
                        evt.detail.shouldLoad = false;
                        return;
                    }

                    // Add search indicator
                    const indicator = element.parentNode.querySelector('.search-indicator');
                    if (indicator) {
                        indicator.style.display = 'inline';
                    }
                }
            } else if (name === 'htmx:afterRequest') {
                const element = evt.detail.elt;
                if (element.hasAttribute('hx-search')) {
                    // Hide search indicator
                    const indicator = element.parentNode.querySelector('.search-indicator');
                    if (indicator) {
                        indicator.style.display = 'none';
                    }
                }
            }
        }
    });

    // HTMX Navigation Extension
    htmx.defineExtension('naga-nav', {
        onEvent: function(name, evt) {
            if (name === 'htmx:afterRequest') {
                const target = evt.detail.target;

                // Update page title if response includes it
                const xhr = evt.detail.xhr;
                const titleHeader = xhr.getResponseHeader('X-Page-Title');
                if (titleHeader) {
                    const pageTitleElement = document.getElementById('pageTitle');
                    if (pageTitleElement) {
                        pageTitleElement.textContent = titleHeader;
                    }
                }

                // Update navigation active state
                const navHeader = xhr.getResponseHeader('X-Nav-Active');
                if (navHeader) {
                    document.querySelectorAll('.nav-item').forEach(item => {
                        item.classList.remove('active');
                    });

                    const activeNav = document.querySelector(`.nav-item[data-page="${navHeader}"]`);
                    if (activeNav) {
                        activeNav.classList.add('active');
                    }
                }

                // Scroll to top for content updates
                if (target.id === 'contentArea') {
                    target.scrollTop = 0;
                }
            }
        }
    });

    // Custom HTMX event handlers
    document.addEventListener('DOMContentLoaded', function() {

        // Handle HTMX configuration
        document.body.addEventListener('htmx:configRequest', function(evt) {
            // Add CSRF token to all HTMX requests
            const csrfToken = window.DashboardApp.csrfToken;
            if (csrfToken) {
                evt.detail.headers['X-CSRFToken'] = csrfToken;
            }

            // Add common headers
            evt.detail.headers['X-Requested-With'] = 'XMLHttpRequest';
        });

        // Handle HTMX errors
        document.body.addEventListener('htmx:responseError', function(evt) {
            console.error('HTMX Response Error:', evt.detail);

            const status = evt.detail.xhr.status;
            let message = 'An error occurred. Please try again.';

            if (status === 403) {
                message = 'You do not have permission to perform this action.';
            } else if (status === 404) {
                message = 'The requested resource was not found.';
            } else if (status === 500) {
                message = 'A server error occurred. Please try again later.';
            }

            window.DashboardApp.showAlert(message, 'error');
        });

        // Handle HTMX network errors
        document.body.addEventListener('htmx:sendError', function(evt) {
            console.error('HTMX Network Error:', evt.detail);
            window.DashboardApp.showAlert('Network error. Please check your connection and try again.', 'error');
        });

        // Handle successful requests
        document.body.addEventListener('htmx:afterRequest', function(evt) {
            if (evt.detail.successful) {
                // Re-initialize dynamic components
                window.DashboardApp.bindDynamicElements();

                // Handle success messages from server
                const successHeader = evt.detail.xhr.getResponseHeader('X-Success-Message');
                if (successHeader) {
                    window.DashboardApp.showAlert(successHeader, 'success');
                }
            }
        });

        // Handle HTMX swaps
        document.body.addEventListener('htmx:afterSwap', function(evt) {
            // Animate new content
            const target = evt.detail.target;
            if (target) {
                target.style.opacity = '0';
                target.style.transform = 'translateY(10px)';

                requestAnimationFrame(() => {
                    target.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    target.style.opacity = '1';
                    target.style.transform = 'translateY(0)';
                });
            }
        });

        // Custom HTMX attributes

        // hx-confirm-delete: Show confirmation for delete actions
        document.body.addEventListener('htmx:confirm', function(evt) {
            const element = evt.detail.elt;
            if (element.hasAttribute('hx-confirm-delete')) {
                const itemName = element.getAttribute('data-item-name') || 'this item';
                evt.detail.question = `Are you sure you want to delete ${itemName}? This action cannot be undone.`;
            }
        });

        // hx-success-redirect: Redirect after successful operation
        document.body.addEventListener('htmx:afterRequest', function(evt) {
            const element = evt.detail.elt;
            if (element.hasAttribute('hx-success-redirect') && evt.detail.successful) {
                const redirectUrl = element.getAttribute('hx-success-redirect');
                if (redirectUrl) {
                    window.location.href = redirectUrl;
                }
            }
        });

        // Auto-submit search forms with debouncing
        document.querySelectorAll('[hx-trigger*="keyup changed delay:"]').forEach(element => {
            if (element.type === 'search' || element.type === 'text') {
                let timeout;
                element.addEventListener('input', function() {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        if (this.value.length >= 2 || this.value.length === 0) {
                            htmx.trigger(this, 'keyup');
                        }
                    }, 300);
                });
            }
        });

        // Handle pagination links
        document.body.addEventListener('click', function(evt) {
            const paginationLink = evt.target.closest('[data-pagination]');
            if (paginationLink) {
                evt.preventDefault();

                const page = paginationLink.getAttribute('data-page');
                const target = paginationLink.getAttribute('data-target') || '#contentArea';
                const baseUrl = paginationLink.getAttribute('data-base-url') || window.location.pathname;

                const targetElement = document.querySelector(target);
                if (targetElement) {
                    const url = new URL(baseUrl, window.location.origin);
                    url.searchParams.set('page', page);

                    targetElement.setAttribute('hx-get', url.toString());
                    htmx.trigger(targetElement, 'htmx:trigger');
                }
            }
        });

        // Handle tab switching with HTMX
        document.body.addEventListener('click', function(evt) {
            const tab = evt.target.closest('[data-hx-tab]');
            if (tab) {
                evt.preventDefault();

                // Update active tab
                tab.closest('.tabs').querySelectorAll('.tab').forEach(t => {
                    t.classList.remove('active');
                });
                tab.classList.add('active');

                // Load tab content
                const tabId = tab.getAttribute('data-hx-tab');
                const contentUrl = tab.getAttribute('data-hx-url');
                const target = tab.getAttribute('data-hx-target') || '.tab-content';

                const targetElement = document.querySelector(target);
                if (targetElement && contentUrl) {
                    targetElement.setAttribute('hx-get', contentUrl);
                    htmx.trigger(targetElement, 'htmx:trigger');
                }
            }
        });

    });

    // Utility functions for HTMX integration
    window.HTMXUtils = {

        // Refresh a specific element
        refresh: function(selector) {
            const element = document.querySelector(selector);
            if (element && element.hasAttribute('hx-get')) {
                htmx.trigger(element, 'htmx:trigger');
            }
        },

        // Load content into target
        loadContent: function(url, target) {
            const targetElement = document.querySelector(target);
            if (targetElement) {
                targetElement.setAttribute('hx-get', url);
                htmx.trigger(targetElement, 'htmx:trigger');
            }
        },

        // Submit form via HTMX
        submitForm: function(formSelector) {
            const form = document.querySelector(formSelector);
            if (form) {
                htmx.trigger(form, 'submit');
            }
        },

        // Show loading state
        showLoading: function(element) {
            element.classList.add('htmx-request');
        },

        // Hide loading state
        hideLoading: function(element) {
            element.classList.remove('htmx-request');
        }
    };

})();
