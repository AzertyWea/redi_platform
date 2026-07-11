/* ========================================
   SERA Foundation – Main JavaScript
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
  // ---- Navigation scroll effect ----
  const nav = document.querySelector('.nav');
  const handleScroll = () => {
    if (window.scrollY > 60) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  };
  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll();

  // ---- Mobile menu ----
  const hamburger = document.querySelector('.nav__hamburger');
  const mobileMenu = document.querySelector('.nav__mobile');
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      mobileMenu.classList.toggle('open');
      document.body.style.overflow = mobileMenu.classList.contains('open') ? 'hidden' : '';
    });
    mobileMenu.querySelectorAll('.nav__link').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('open');
        mobileMenu.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  // ---- Dark mode toggle ----
  const themeToggle = document.querySelectorAll('.theme-toggle');
  const storedTheme = localStorage.getItem('sera-theme');
  if (storedTheme) {
    document.documentElement.setAttribute('data-theme', storedTheme);
  }
  themeToggle.forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('sera-theme', next);
      themeToggle.forEach(b => {
        b.innerHTML = next === 'dark' ? '&#9728;' : '&#9790;';
      });
    });
    btn.innerHTML = (document.documentElement.getAttribute('data-theme') === 'dark') ? '&#9728;' : '&#9790;';
  });

  // ---- Scroll reveal animations ----
  const reveals = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  reveals.forEach(el => revealObserver.observe(el));

  // ---- Animated counters ----
  const counters = document.querySelectorAll('[data-count]');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.getAttribute('data-count'), 10);
        const suffix = el.getAttribute('data-suffix') || '';
        const duration = 2000;
        const start = performance.now();
        const animate = (now) => {
          const elapsed = now - start;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.floor(target * eased).toLocaleString() + suffix;
          if (progress < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(el => counterObserver.observe(el));

  // ---- Donation amount selector ----
  const donateAmounts = document.querySelectorAll('.donate-amount');
  const customInput = document.querySelector('.donate-custom input');
  donateAmounts.forEach(btn => {
    btn.addEventListener('click', () => {
      donateAmounts.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (customInput) customInput.value = '';
    });
  });
  if (customInput) {
    customInput.addEventListener('focus', () => {
      donateAmounts.forEach(b => b.classList.remove('active'));
    });
  }

  // ---- Project filter ----
  const filters = document.querySelectorAll('.project-filter');
  const projectCards = document.querySelectorAll('.project-card');
  filters.forEach(filter => {
    filter.addEventListener('click', () => {
      filters.forEach(f => f.classList.remove('active'));
      filter.classList.add('active');
      const cat = filter.getAttribute('data-filter');
      projectCards.forEach(card => {
        if (cat === 'all' || card.getAttribute('data-category') === cat) {
          card.style.display = '';
          setTimeout(() => card.style.opacity = '1', 10);
        } else {
          card.style.opacity = '0';
          setTimeout(() => card.style.display = 'none', 300);
        }
      });
    });
  });

  // ---- Contact form ----
  const contactForm = document.querySelector('#contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const origText = btn.innerHTML;
      btn.innerHTML = '&#10003; Message Sent!';
      btn.style.background = '#22c55e';
      btn.disabled = true;
      setTimeout(() => {
        btn.innerHTML = origText;
        btn.style.background = '';
        btn.disabled = false;
        contactForm.reset();
      }, 3000);
    });
  }

  // ---- Back to top ----
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 400) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    }, { passive: true });
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ---- Progress bar animation ----
  const progressBars = document.querySelectorAll('.project-card__progress-fill');
  const progressObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const w = el.getAttribute('data-progress');
        el.style.width = w + '%';
        progressObserver.unobserve(el);
      }
    });
  }, { threshold: 0.3 });
  progressBars.forEach(bar => {
    bar.style.width = '0%';
    progressObserver.observe(bar);
  });

  // ---- Smooth page transitions ----
  document.querySelectorAll('a[href]').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href.endsWith('.html') && !href.startsWith('http')) {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity .25s ease';
        setTimeout(() => {
          window.location.href = href;
        }, 250);
      });
    }
  });
  document.body.style.opacity = '1';
  document.body.style.transition = 'opacity .25s ease';
});
