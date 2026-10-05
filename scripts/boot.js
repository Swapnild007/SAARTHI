(() => {
  // Boot owns only non-interactive page lifecycle.
  // Conversation transport belongs exclusively to scripts/app.js.
  try {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    window.scrollTo(0, 0);
    requestAnimationFrame(() => window.scrollTo(0, 0));
  } catch (_) {}

  const splash = document.getElementById('sudarshanSplash');
  const splashVideo = document.getElementById('saarthiSplashVideo');
  const fallback = document.getElementById('splashFallbackBrand');

  document.body.classList.add('splash-active');
  if (fallback) fallback.style.display = 'none';

  let closed = false;
  const closeSplash = () => {
    if (closed) return;
    closed = true;
    splash?.classList.add('hide');
    document.body.classList.remove('splash-active');
  };

  const showFallback = (delay = 600) => {
    if (fallback) fallback.style.display = 'grid';
    window.setTimeout(closeSplash, delay);
  };

  splashVideo?.addEventListener('error', () => showFallback());
  splashVideo?.addEventListener('ended', closeSplash);

  if (splashVideo) {
    splashVideo.play?.().catch(() => showFallback());
  } else {
    closeSplash();
  }

  window.setTimeout(closeSplash, 6000);
})();
