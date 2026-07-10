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
  initSmoothScroll();
  initCardAnimations();
  initTooltips();
  initSearchableSelect();
  initCharCounters();
  initLiveSearch();
  initBackToTop();
});

function initSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const overlay = document.getElementById('sidebar-overlay');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      if (overlay) overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
    });
    document.addEventListener('click', function (e) {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('open');
        if (overlay) overlay.style.display = 'none';
      }
    });
  }
  if (overlay) {
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.style.display = 'none';
    });
  }
}

function initActiveNav() {
  var path = window.location.pathname;
  document.querySelectorAll('.sidebar-menu a').forEach(function(link) {
    var href = link.getAttribute('href');
    if (href && (href === path || (href !== '/' && href !== '/logout' && path.startsWith(href)))) {
      link.classList.add('active');
    }
  });
}

function initEriRing() {
  var ring = document.querySelector('.score-circle');
  if (ring) {
    var score = parseFloat(ring.dataset.score) || 0;
    var offset = 314 - (314 * score / 100);
    setTimeout(function() { ring.style.strokeDashoffset = offset; }, 200);
  }
}

function initProgressBars() {
  document.querySelectorAll('.progress-bar[data-width]').forEach(function(bar) {
    var w = bar.dataset.width;
    setTimeout(function() { bar.style.width = w + '%'; }, 300);
  });
}

function initAlerts() {
  document.querySelectorAll('.alert').forEach(function(alert) {
    var closeBtn = alert.querySelector('.close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() { dismissAlert(alert); });
    }
    var autohide = alert.dataset.autohide;
    if (autohide !== undefined) {
      var delay = parseInt(autohide) || 4000;
      setTimeout(function() { if (alert.parentNode) dismissAlert(alert); }, delay);
    }
  });
}

function dismissAlert(alert) {
  alert.style.transition = 'opacity 0.3s, transform 0.3s';
  alert.style.opacity = '0';
  alert.style.transform = 'translateX(20px)';
  setTimeout(function() { if (alert.parentNode) alert.remove(); }, 300);
}

function initDeleteConfirm() {
  document.querySelectorAll('[data-confirm]').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });
}

function initTableSearch() {
  var tableSearch = document.getElementById('table-search');
  if (tableSearch) {
    tableSearch.addEventListener('input', function() {
      var q = this.value.toLowerCase();
      document.querySelectorAll('.searchable-row').forEach(function(row) {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
}

function initStatCounters() {
  document.querySelectorAll('.stat-count[data-target]').forEach(function(el) {
    var target = parseFloat(el.dataset.target);
    var isFloat = el.dataset.float === 'true';
    var duration = 1000;
    var step = target / (duration / 16);
    var current = 0;
    var timer = setInterval(function() {
      current = Math.min(current + step, target);
      el.textContent = isFloat ? current.toFixed(1) : Math.floor(current);
      if (current >= target) clearInterval(timer);
    }, 16);
  });
}

function initFileInputs() {
  document.querySelectorAll('input[type="file"]').forEach(function(input) {
    input.addEventListener('change', function() {
      var label = document.querySelector('label[for="' + this.id + '"] .file-name');
      if (label) label.textContent = this.files[0]?.name || 'No file chosen';
    });
  });
}

function initFormValidation() {
  document.querySelectorAll('form[data-validate]').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      var valid = true;
      this.querySelectorAll('[required]').forEach(function(field) {
        if (!field.value.trim()) {
          field.classList.add('error');
          valid = false;
        } else {
          field.classList.remove('error');
        }
      });
      if (!valid) {
        e.preventDefault();
        var firstErr = this.querySelector('.error');
        if (firstErr) firstErr.focus();
      }
    });
    form.querySelectorAll('[required]').forEach(function(field) {
      field.addEventListener('input', function() { this.classList.remove('error'); });
    });
  });
}

function initLoadingButtons() {
  document.querySelectorAll('.btn-loading').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var form = this.closest('form');
      if (form && !form.checkValidity()) return;
      var original = this.innerHTML;
      this.dataset.originalHtml = original;
      this.innerHTML = '<span class="spinner"></span><span class="btn-text">Loading...</span>';
      this.disabled = true;
      this.classList.add('loading');
    });
  });
}

function initSelectPlaceholder() {
  document.querySelectorAll('select.form-control').forEach(function(select) {
    select.addEventListener('change', function() {
      if (this.value) this.style.color = 'var(--text)';
    });
  });
}

function initResponsiveTables() {
  document.querySelectorAll('.table-wrap table, .corp-table').forEach(function(table) {
    var parent = table.closest('.card, .corp-panel, .content');
    if (parent && table.scrollWidth > parent.clientWidth) {
      if (!table.closest('.table-wrap')) {
        var wrap = document.createElement('div');
        wrap.className = 'table-wrap';
        wrap.style.border = 'none';
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);
      }
    }
  });
}

function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

function initCardAnimations() {
  if (window.IntersectionObserver) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    document.querySelectorAll('.card, .stat-card, .corp-panel, .profile-section').forEach(function(el) {
      if (!el.classList.contains('no-animate')) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(16px)';
        el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        observer.observe(el);
      }
    });
  }
}

function initTooltips() {
  document.querySelectorAll('[data-tooltip]').forEach(function(el) {
    el.addEventListener('mouseenter', function(e) {
      var tip = document.createElement('div');
      tip.className = 'custom-tooltip';
      tip.textContent = this.dataset.tooltip;
      tip.style.cssText = 'position:fixed;background:#1A0A0A;color:#fff;padding:6px 11px;border-radius:6px;font-size:11px;font-weight:500;pointer-events:none;z-index:9999;white-space:nowrap';
      document.body.appendChild(tip);
      var rect = this.getBoundingClientRect();
      tip.style.left = (rect.left + rect.width / 2 - tip.offsetWidth / 2) + 'px';
      tip.style.top = (rect.top - tip.offsetHeight - 8) + 'px';
      this._tooltip = tip;
    });
    el.addEventListener('mouseleave', function() {
      if (this._tooltip) { this._tooltip.remove(); this._tooltip = null; }
    });
  });
}

function initSearchableSelect() {
  document.querySelectorAll('select[data-searchable]').forEach(function(select) {
    select.addEventListener('focus', function() { this.size = Math.min(this.options.length, 8); });
    select.addEventListener('blur', function() { this.size = 1; });
    select.addEventListener('change', function() { this.size = 1; });
  });
}

function initCharCounters() {
  document.querySelectorAll('textarea[data-maxlength]').forEach(function(textarea) {
    var max = parseInt(textarea.dataset.maxlength);
    var counter = document.createElement('div');
    counter.className = 'char-counter';
    counter.style.cssText = 'font-size:11px;color:var(--text-secondary);text-align:right;margin-top:4px';
    counter.textContent = '0 / ' + max;
    textarea.parentNode.appendChild(counter);
    textarea.addEventListener('input', function() {
      var len = this.value.length;
      if (len > max) { this.value = this.value.slice(0, max); len = max; }
      counter.textContent = len + ' / ' + max;
      counter.style.color = len > max * 0.9 ? 'var(--toast-error)' : 'var(--text-secondary)';
    });
  });
}

function initLiveSearch() {
  var liveSearch = document.getElementById('live-search');
  if (liveSearch) {
    var targetId = liveSearch.dataset.target;
    var url = liveSearch.dataset.url;
    var timer;
    liveSearch.addEventListener('input', function() {
      clearTimeout(timer);
      timer = setTimeout(function() {
        var q = liveSearch.value;
        var container = document.getElementById(targetId);
        if (q.length < 2) { container.innerHTML = ''; return; }
        container.innerHTML = '<div class="empty-state" style="padding:20px"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
        fetch(url + '?q=' + encodeURIComponent(q))
          .then(function(r) { return r.text(); })
          .then(function(html) { container.innerHTML = html; })
          .catch(function() { container.innerHTML = '<div class="empty-state" style="padding:20px">Error searching</div>'; });
      }, 300);
    });
  }
}

function initBackToTop() {
  var btn = document.getElementById('back-to-top');
  if (!btn) {
    btn = document.createElement('button');
    btn.id = 'back-to-top';
    btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    btn.style.cssText = 'position:fixed;bottom:90px;right:24px;width:40px;height:40px;border-radius:50%;background:var(--primary);color:#fff;border:none;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,0.2);z-index:300;display:none;transition:all .2s';
    document.body.appendChild(btn);
    btn.addEventListener('click', function() { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  }
  window.addEventListener('scroll', function() {
    btn.style.display = window.scrollY > 400 ? 'flex' : 'none';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
  });
}

function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3500;
  var container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  var toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  var icons = { success: 'check-circle', error: 'times-circle', warning: 'exclamation-triangle', info: 'info-circle' };
  toast.innerHTML = '<i class="fas fa-' + (icons[type] || icons.info) + '"></i> ' + message;
  container.appendChild(toast);
  requestAnimationFrame(function() { toast.classList.add('show'); });
  setTimeout(function() {
    toast.classList.remove('show');
    setTimeout(function() { toast.remove(); }, 300);
  }, duration);
}

function showConfirm(message, onConfirm) {
  if (confirm(message)) onConfirm();
}

function loadPrograms(deptName, selectId) {
  var sel = document.getElementById(selectId);
  if (!deptName) {
    sel.innerHTML = '<option value="">-- Select school above first --</option>';
    return;
  }
  sel.innerHTML = '<option value="">Loading...</option>';
  fetch("/student/programs-by-department?name=" + encodeURIComponent(deptName))
    .then(function(r) { return r.json(); })
    .then(function(programs) {
      sel.innerHTML = '<option value="">-- Select program --</option>';
      programs.forEach(function(p) {
        var opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        sel.appendChild(opt);
      });
    });
}
