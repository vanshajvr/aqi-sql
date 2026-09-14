// Animates the first number found in an element's text on page load, e.g.
// "Avg AQI 355.8" counts up to 355.8 while the surrounding text stays put.
// Deliberately does NOT touch .kpi-value - those often hold station names
// or dates ("Apr 2020"), and animating a year like 2020 from 0 would look
// broken rather than polished. Only .kpi-sub and .badge get this - they're
// the elements whose primary content actually is a number.
function animateNumber(el, duration) {
  duration = duration || 900;
  const original = el.textContent;
  const match = original.match(/-?\d+(\.\d+)?/);
  if (!match) return; // no number in this element - leave it alone

  const target = parseFloat(match[0]);
  const decimals = match[1] ? match[1].length - 1 : 0;
  const prefix = original.slice(0, match.index);
  const suffix = original.slice(match.index + match[0].length);

  const start = performance.now();
  function frame(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = target * eased;
    el.textContent = prefix + current.toFixed(decimals) + suffix;
    if (progress < 1) {
      requestAnimationFrame(frame);
    } else {
      el.textContent = original; // snap to exact original text, avoids float drift
    }
  }
  requestAnimationFrame(frame);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".kpi-sub, .badge").forEach((el) => animateNumber(el));
});