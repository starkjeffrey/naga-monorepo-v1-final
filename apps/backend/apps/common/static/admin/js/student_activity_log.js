/**
 * JavaScript enhancements for StudentActivityLog admin interface
 */

(function () {
  'use strict';

  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', function () {
    initializeActivityLogAdmin();
  });

  function initializeActivityLogAdmin() {
    // Initialize tooltips
    initializeTooltips();

    // Initialize quick date range selector
    initializeDateRangeSelector();

    // Initialize export functionality
    initializeExportButton();

    // Initialize search enhancements
    initializeSearchEnhancements();

    // Initialize filter persistence
    initializeFilterPersistence();
  }

  /**
   * Initialize Bootstrap-style tooltips
   */
  function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(function (element) {
      // Store original title
      const originalTitle = element.getAttribute('title');

      // Remove title to prevent browser tooltip
      element.removeAttribute('title');

      // Add custom tooltip on hover
      element.addEventListener('mouseenter', function (e) {
        showTooltip(e.target, originalTitle);
      });

      element.addEventListener('mouseleave', function (e) {
        hideTooltip();
      });
    });
  }

  function showTooltip(element, text) {
    hideTooltip(); // Remove any existing tooltip

    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
            position: absolute;
            background-color: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            z-index: 10000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
        `;

    document.body.appendChild(tooltip);

    // Position tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.left =
      rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
    tooltip.style.top =
      rect.top - tooltip.offsetHeight - 5 + window.scrollY + 'px';

    // Fade in
    setTimeout(function () {
      tooltip.style.opacity = '1';
    }, 10);
  }

  function hideTooltip() {
    const existingTooltip = document.querySelector('.custom-tooltip');
    if (existingTooltip) {
      existingTooltip.remove();
    }
  }

  /**
   * Initialize date range selector functionality
   */
  function initializeDateRangeSelector() {
    const quickDateRange = document.querySelector(
      'select[name="quick_date_range"]'
    );
    if (!quickDateRange) return;

    quickDateRange.addEventListener('change', function (e) {
      const value = e.target.value;
      const dateFrom = document.querySelector('input[name="date_from"]');
      const dateTo = document.querySelector('input[name="date_to"]');

      if (!dateFrom || !dateTo) return;

      const today = new Date();
      let startDate, endDate;

      switch (value) {
        case 'today':
          startDate = endDate = today;
          break;
        case 'yesterday':
          startDate = endDate = new Date(today.getTime() - 24 * 60 * 60 * 1000);
          break;
        case 'last_7_days':
          startDate = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
          endDate = today;
          break;
        case 'last_30_days':
          startDate = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
          endDate = today;
          break;
        case 'last_90_days':
          startDate = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
          endDate = today;
          break;
        case 'this_month':
          startDate = new Date(today.getFullYear(), today.getMonth(), 1);
          endDate = today;
          break;
        case 'last_month':
          const lastMonth = new Date(
            today.getFullYear(),
            today.getMonth() - 1,
            1
          );
          startDate = lastMonth;
          endDate = new Date(today.getFullYear(), today.getMonth(), 0);
          break;
        case 'this_year':
          startDate = new Date(today.getFullYear(), 0, 1);
          endDate = today;
          break;
        default:
          return; // Custom range
      }

      // Format dates as YYYY-MM-DD
      dateFrom.value = formatDate(startDate);
      dateTo.value = formatDate(endDate);
    });
  }

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Initialize export button with loading indicator
   */
  function initializeExportButton() {
    const exportActions = document.querySelectorAll(
      'button[name="action"][value="export_as_csv"]'
    );

    exportActions.forEach(function (button) {
      button.addEventListener('click', function (e) {
        // Check if any items are selected
        const checkedBoxes = document.querySelectorAll(
          'input[name="_selected_action"]:checked'
        );
        if (checkedBoxes.length === 0) {
          e.preventDefault();
          alert('Please select at least one log entry to export.');
          return;
        }

        // Add loading indicator
        const originalText = button.textContent;
        button.disabled = true;
        button.innerHTML =
          originalText + ' <span class="loading-indicator"></span>';

        // Re-enable after a delay (the form submission will happen)
        setTimeout(function () {
          button.disabled = false;
          button.textContent = originalText;
        }, 3000);
      });
    });
  }

  /**
   * Enhance search functionality
   */
  function initializeSearchEnhancements() {
    const searchInput = document.querySelector('#searchbar');
    if (!searchInput) return;

    // Add clear button
    const clearButton = document.createElement('button');
    clearButton.type = 'button';
    clearButton.className = 'clear-search';
    clearButton.innerHTML = '×';
    clearButton.style.cssText = `
            position: absolute;
            right: 40px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: #999;
            display: none;
        `;

    searchInput.parentElement.style.position = 'relative';
    searchInput.parentElement.appendChild(clearButton);

    // Show/hide clear button
    searchInput.addEventListener('input', function () {
      clearButton.style.display = this.value ? 'block' : 'none';
    });

    // Clear search
    clearButton.addEventListener('click', function () {
      searchInput.value = '';
      clearButton.style.display = 'none';
      searchInput.form.submit();
    });

    // Initial state
    if (searchInput.value) {
      clearButton.style.display = 'block';
    }
  }

  /**
   * Save and restore filter state
   */
  function initializeFilterPersistence() {
    const STORAGE_KEY = 'studentActivityLogFilters';

    // Save current filters
    const saveFilters = function () {
      const filters = {};
      const params = new URLSearchParams(window.location.search);

      for (const [key, value] of params) {
        if (key !== 'p') {
          // Exclude page number
          filters[key] = value;
        }
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    };

    // Add "Restore Filters" button
    const actionRow = document.querySelector('.actions');
    if (actionRow) {
      const restoreButton = document.createElement('button');
      restoreButton.type = 'button';
      restoreButton.className = 'button default';
      restoreButton.textContent = 'Restore Last Filters';
      restoreButton.style.marginLeft = '10px';

      restoreButton.addEventListener('click', function () {
        const savedFilters = localStorage.getItem(STORAGE_KEY);
        if (savedFilters) {
          const filters = JSON.parse(savedFilters);
          const params = new URLSearchParams(filters);
          window.location.search = params.toString();
        }
      });

      // Only show if we have saved filters
      const savedFilters = localStorage.getItem(STORAGE_KEY);
      if (savedFilters && Object.keys(JSON.parse(savedFilters)).length > 0) {
        actionRow.appendChild(restoreButton);
      }
    }

    // Save current filters
    if (window.location.search) {
      saveFilters();
    }
  }

  /**
   * Add keyboard shortcuts
   */
  document.addEventListener('keydown', function (e) {
    // Ctrl/Cmd + E for export
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
      e.preventDefault();
      const exportButton = document.querySelector(
        'button[value="export_as_csv"]'
      );
      if (exportButton) {
        exportButton.click();
      }
    }

    // Ctrl/Cmd + F to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault();
      const searchInput = document.querySelector('#searchbar');
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }
  });
})();
