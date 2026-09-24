/**
 * Portfolio — Minimal JS enhancements
 */
document.addEventListener('DOMContentLoaded', () => {
  // ── Mobile menu toggle ─────────────────
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mainNav = document.getElementById('main-nav');
  if (menuBtn && mainNav) {
    menuBtn.addEventListener('click', () => {
      mainNav.classList.toggle('open');
      menuBtn.classList.toggle('active');
    });
  }

  // ── Alert dismiss ──────────────────────
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 250);
    });
  });

  // ── Header scroll effect ───────────────
  const header = document.getElementById('site-header');
  if (header) {
    let lastY = 0;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      header.style.borderBottomColor = y > 40
        ? 'rgba(255,255,255,0.08)'
        : 'transparent';
      lastY = y;
    }, { passive: true });
  }
});
