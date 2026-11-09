// Shrink text inside each [data-fit] box until it fits, never below data-min (px).
// Runs only after the webfonts have loaded, so measurements use Archivo, not a fallback.
// Flags overflow on <html data-overflow="1"> so build.py can refuse the page.
function fitAll() {
  document.querySelectorAll("[data-fit]").forEach(function (box) {
    var el = box.querySelector(box.dataset.fit);
    if (!el) return;
    var min = parseFloat(box.dataset.min || "28");
    var size = parseFloat(getComputedStyle(el).fontSize);
    var children = box.dataset.scale ? box.querySelectorAll(box.dataset.scale) : [];
    var base = Array.prototype.map.call(children, function (c) { return parseFloat(getComputedStyle(c).fontSize); });
    var start = size;
    // bottom-anchored boxes overflow upwards, which scrollHeight does not report: check the first child's top too
    function fits() {
      var top = box.firstElementChild ? box.firstElementChild.getBoundingClientRect().top - box.getBoundingClientRect().top : 0;
      return top >= -1 && box.scrollHeight <= box.clientHeight + 1 && el.scrollWidth <= box.clientWidth + 1;
    }
    while (!fits() && size > min) {
      size -= 1;
      el.style.fontSize = size + "px";
      // other elements in the box (e.g. affiliations) shrink in proportion
      Array.prototype.forEach.call(children, function (c, i) { c.style.fontSize = (base[i] * size / start) + "px"; });
    }
    box.dataset.fittedSize = size;
    if (!fits()) { box.classList.add("overflow"); document.documentElement.dataset.overflow = "1"; }
  });
  document.documentElement.dataset.fitted = "1";
}
document.fonts.ready.then(fitAll);
