/* ==========================================================================
   Money Mate — shared scripts (used by every page)
   ========================================================================== */
(function () {
  const BOT_USERNAME = '@HeyMoneyMate_bot';

  // ---------- Toasts ----------
  function getToastContainer() {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      c.setAttribute('role', 'status');
      c.setAttribute('aria-live', 'polite');
      document.body.appendChild(c);
    }
    return c;
  }

  function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
    t.appendChild(document.createTextNode(msg)); // textNode = no HTML injection
    getToastContainer().appendChild(t);
    setTimeout(() => {
      t.classList.add('hide');
      setTimeout(() => t.remove(), 400);
    }, 3000);
  }
  window.showToast = showToast;

  // ---------- Telegram links ----------
  // Links open Telegram normally; we additionally copy the bot username
  // as a convenience (useful on desktop where t.me may not open the app).
  document.querySelectorAll('a.tg-link').forEach(el => {
    el.addEventListener('click', () => {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(BOT_USERNAME)
          .then(() => showToast('Opening Telegram… ' + BOT_USERNAME + ' copied 🚀'))
          .catch(() => showToast('Opening Telegram… 🚀'));
      } else {
        showToast('Opening Telegram… 🚀');
      }
    });
  });

  // ---------- Mobile nav ----------
  const toggle = document.querySelector('.nav-toggle');
  const links = document.getElementById('nav-links');
  if (toggle && links) {
    const setOpen = (open) => {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      links.classList.toggle('open', open);
    };
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });
    links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setOpen(false)));
    document.addEventListener('click', (e) => {
      if (!links.contains(e.target) && e.target !== toggle) setOpen(false);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && links.classList.contains('open')) {
        setOpen(false);
        toggle.focus();
      }
    });
    window.matchMedia('(min-width: 901px)').addEventListener('change', (mq) => {
      if (mq.matches) setOpen(false);
    });
  }

  // ---------- Footer year ----------
  document.querySelectorAll('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });

  // ---------- Haptic Feedback on Scroll ----------
  let lastScrollY = window.scrollY;
  let scrollAccumulator = 0;
  // Many browsers require a user gesture before allowing vibration
  let userHasInteracted = false;
  
  const recordInteraction = () => {
    userHasInteracted = true;
    document.removeEventListener('click', recordInteraction);
    document.removeEventListener('touchstart', recordInteraction);
    document.removeEventListener('keydown', recordInteraction);
  };
  
  document.addEventListener('click', recordInteraction, { passive: true });
  document.addEventListener('touchstart', recordInteraction, { passive: true });
  document.addEventListener('keydown', recordInteraction, { passive: true });

  window.addEventListener('scroll', () => {
    if (!userHasInteracted || !navigator.vibrate) return;
    
    const currentScrollY = window.scrollY;
    const diff = Math.abs(currentScrollY - lastScrollY);
    scrollAccumulator += diff;
    lastScrollY = currentScrollY;

    // Trigger a very short haptic pulse every 150 pixels of scrolling
    if (scrollAccumulator > 150) {
      scrollAccumulator = 0;
      navigator.vibrate(25); // 3ms is a subtle "tick" on supported devices
    }
  }, { passive: true });

})();
