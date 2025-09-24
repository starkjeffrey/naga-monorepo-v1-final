// CRUD Framework JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // Debug: Check if links exist
  const links = document.querySelectorAll('td a[href*="/people/students/"]');
  console.log('Student detail links found:', links.length);

  // Ensure links are clickable and add debug
  links.forEach((link) => {
    link.style.position = 'relative';
    link.style.zIndex = '10';

    // Add click event listener to debug
    link.addEventListener('click', function (e) {
      console.log('Link clicked:', this.href);
      // Don't prevent default - let the link work normally
    });
  });

  // Check if something is preventing clicks globally
  document.addEventListener(
    'click',
    function (e) {
      if (e.target.tagName === 'A' || e.target.closest('a')) {
        console.log('Click on link detected:', e.target);
      }
    },
    true
  );
  // Column Toggle Functionality
  const columnToggleButton = document.getElementById('column-toggle-button');
  const columnDropdown = document.getElementById('column-dropdown');
  const closeButton = document.getElementById('close-column-dropdown');
  const columnCheckboxes = document.querySelectorAll('.column-toggle');
  const hiddenCountSpan = document.getElementById('hidden-columns-count');

  if (columnToggleButton && columnDropdown) {
    // Toggle dropdown
    columnToggleButton.addEventListener('click', function (e) {
      e.stopPropagation();
      columnDropdown.classList.toggle('hidden');
      const icon = document.getElementById('column-toggle-icon');
      if (icon) {
        icon.classList.toggle('rotate-180');
      }
    });

    closeButton?.addEventListener('click', function () {
      columnDropdown.classList.add('hidden');
      const icon = document.getElementById('column-toggle-icon');
      if (icon) {
        icon.classList.remove('rotate-180');
      }
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
      if (
        !columnDropdown.contains(e.target) &&
        !columnToggleButton.contains(e.target)
      ) {
        columnDropdown.classList.add('hidden');
        const icon = document.getElementById('column-toggle-icon');
        if (icon) {
          icon.classList.remove('rotate-180');
        }
      }
    });
  }

  // Column visibility logic
  columnCheckboxes.forEach(function (checkbox) {
    const columnKey = checkbox.dataset.key;
    const savedState = localStorage.getItem(`column_${columnKey}`);

    // Initialize checkbox state from localStorage
    if (savedState === null) {
      checkbox.checked = true; // Default to visible
    } else {
      checkbox.checked = savedState === 'visible';
    }

    // Apply initial visibility
    toggleColumn(columnKey, checkbox.checked);

    // Handle checkbox change
    checkbox.addEventListener('change', function () {
      toggleColumn(columnKey, this.checked);
      localStorage.setItem(
        `column_${columnKey}`,
        this.checked ? 'visible' : 'hidden'
      );
      updateHiddenCount();
    });
  });

  function toggleColumn(columnKey, show) {
    // Toggle header
    const headers = document.querySelectorAll(`th[data-key="${columnKey}"]`);
    headers.forEach((header) => {
      header.style.display = show ? '' : 'none';
    });

    // Toggle cells
    const cells = document.querySelectorAll(`td[data-key="${columnKey}"]`);
    cells.forEach((cell) => {
      cell.style.display = show ? '' : 'none';
    });
  }

  function updateHiddenCount() {
    const hiddenCount = Array.from(columnCheckboxes).filter(
      (cb) => !cb.checked
    ).length;
    if (hiddenCountSpan) {
      if (hiddenCount > 0) {
        hiddenCountSpan.textContent = hiddenCount;
        hiddenCountSpan.classList.remove('hidden');
      } else {
        hiddenCountSpan.classList.add('hidden');
      }
    }
  }

  // Initial count update
  updateHiddenCount();

  // Handle sorting indicators
  const sortableHeaders = document.querySelectorAll('.sortable-header');
  sortableHeaders.forEach((header) => {
    header.style.cursor = 'pointer';
  });
});
