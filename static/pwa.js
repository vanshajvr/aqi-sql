// Install as an app: registers the service worker and shows an "Install app"
// button where the browser supports it (Chrome / Edge on Android, Windows,
// Mac, ChromeOS). iPhone and iPad have no install prompt, so there the button
// explains Safari's "Add to Home Screen" instead. Hidden once installed.
(function () {
  const standalone = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);   // iPadOS reports as a Mac

  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }

  let deferred = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();                 // show our own button instead of the browser's mini-bar
    deferred = e;
    show();
  });
  window.addEventListener("appinstalled", () => { deferred = null; hide(); });

  function button() { return document.getElementById("install-app"); }
  function show() { const b = button(); if (b && !standalone()) b.hidden = false; }
  function hide() { const b = button(); if (b) b.hidden = true; closeHelp(); }

  function closeHelp() { const h = document.getElementById("install-help"); if (h) h.hidden = true; }

  document.addEventListener("DOMContentLoaded", () => {
    const b = button();
    if (!b || standalone()) return;
    if (isIOS) show();                  // Safari: explain Add to Home Screen
    b.addEventListener("click", async () => {
      if (deferred) {
        deferred.prompt();
        const { outcome } = await deferred.userChoice;
        if (outcome === "accepted") hide();
        deferred = null;
        return;
      }
      const help = document.getElementById("install-help");
      if (help) help.hidden = !help.hidden;
    });
    const close = document.getElementById("install-help-close");
    if (close) close.addEventListener("click", closeHelp);
  });
})();
