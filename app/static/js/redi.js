document.addEventListener('DOMContentLoaded', function () {
  initSidebar();
  initActiveNav();
  initEriRing();
  initProgressBars();
  initAlerts();
  initDeleteConfirm();
  initTableSearch();
  initStatCounters();
  initFileInputs();
  initFormValidation();
  initLoadingButtons();
  initSelectPlaceholder();
  initResponsiveTables();
});

function initSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const overlay = document.getElementById('sidebar-overlay');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (overlay) overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
    });
    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('open');
        if (overlay) overlay.style.display = 'none';
      }
    });
  }
  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.style.display = 'none';
    });
  }
}

function initActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-menu a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href === path || (href !== '/' && path.startsWith(href)))) {
      link.classList.add('active');
    }
  });
}

function initEriRing() {
  const ring = document.querySelector('.score-circle');
  if (ring) {
    const score = parseFloat(ring.dataset.score) || 0;
    const offset = 314 - (314 * score / 100);
    setTimeout(() => { ring.style.strokeDashoffset = offset; }, 200);
  }
}

function initProgressBars() {
  document.querySelectorAll('.progress-bar[data-width]').forEach(bar => {
    const w = bar.dataset.width;
    setTimeout(() => { bar.style.width = w + '%'; }, 300);
  });
}

function initAlerts() {
  document.querySelectorAll('.alert').forEach(alert => {
    const closeBtn = alert.querySelector('.close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => dismissAlert(alert));
    }
    const autohide = alert.dataset.autohide;
    if (autohide !== undefined) {
      const delay = parseInt(autohide) || 4000;
      setTimeout(() => { if (alert.parentNode) dismissAlert(alert); }, delay);
    }
  });
}

function dismissAlert(alert) {
  alert.style.transition = 'opacity 0.3s';
  alert.style.opacity = '0';
  setTimeout(() => { if (alert.parentNode) alert.remove(); }, 300);
}

function initDeleteConfirm() {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });
}

function initTableSearch() {
  const tableSearch = document.getElementById('table-search');
  if (tableSearch) {
    tableSearch.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll('.searchable-row').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
}

function initStatCounters() {
  document.querySelectorAll('.stat-count[data-target]').forEach(el => {
    const target = parseFloat(el.dataset.target);
    const isFloat = el.dataset.float === 'true';
    const duration = 1000;
    const step = target / (duration / 16);
    let current = 0;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = isFloat ? current.toFixed(1) : Math.floor(current);
      if (current >= target) clearInterval(timer);
    }, 16);
  });
}

function initFileInputs() {
  document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function () {
      const label = document.querySelector(`label[for="${this.id}"] .file-name`);
      if (label) label.textContent = this.files[0]?.name || 'No file chosen';
    });
  });
}

function initFormValidation() {
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', function (e) {
      let valid = true;
      this.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) {
          field.classList.add('error');
          valid = false;
        } else {
          field.classList.remove('error');
        }
      });
      if (!valid) {
        e.preventDefault();
        const firstErr = this.querySelector('.error');
        if (firstErr) firstErr.focus();
      }
    });
    form.querySelectorAll('[required]').forEach(field => {
      field.addEventListener('input', () => field.classList.remove('error'));
    });
  });
}

function initLoadingButtons() {
  document.querySelectorAll('.btn-loading').forEach(btn => {
    btn.addEventListener('click', function () {
      const form = this.closest('form');
      if (form && !form.checkValidity()) return;
      const original = this.innerHTML;
      this.dataset.originalHtml = original;
      this.innerHTML = '<span class="spinner"></span><span class="btn-text">Loading...</span>';
      this.disabled = true;
      this.classList.add('loading');
      const formId = this.dataset.loadingForm;
      if (formId) {
        const targetForm = document.getElementById(formId);
        if (targetForm) targetForm.addEventListener('submit', () => {});
      }
    });
  });
}

function initSelectPlaceholder() {
  document.querySelectorAll('select.form-control').forEach(select => {
    select.addEventListener('change', function () {
      if (this.value) this.style.color = 'var(--text)';
    });
  });
}

function initResponsiveTables() {
  document.querySelectorAll('.table-wrap, .corp-table').forEach(table => {
    const parent = table.closest('.card, .corp-panel');
    if (parent && table.scrollWidth > parent.clientWidth) {
      if (!table.closest('.table-wrap')) {
        const wrap = document.createElement('div');
        wrap.className = 'table-wrap';
        wrap.style.border = 'none';
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);
      }
    }
  });
}

function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3500;
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  const icons = { success: 'check-circle', error: 'times-circle', warning: 'exclamation-triangle', info: 'info-circle' };
  toast.innerHTML = '<i class="fas fa-' + (icons[type] || icons.info) + '"></i> ' + message;
  container.appendChild(toast);
  requestAnimationFrame(() => { toast.classList.add('show'); });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showConfirm(message, onConfirm) {
  if (confirm(message)) onConfirm();
}

function loadPrograms(deptName, selectId) {
  const sel = document.getElementById(selectId);
  if (!deptName) {
    sel.innerHTML = '<option value="">-- Select school above first --</option>';
    return;
  }
  sel.innerHTML = '<option value="">Loading...</option>';
  fetch("/student/programs-by-department?name=" + encodeURIComponent(deptName))
    .then(r => r.json())
    .then(programs => {
      sel.innerHTML = '<option value="">-- Select program --</option>';
      programs.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        sel.appendChild(opt);
      });
    });
}
