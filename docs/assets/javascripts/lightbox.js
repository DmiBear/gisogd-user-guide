/* Accessible image viewer. No dependency; reinitialized on Material instant navigation. */
(function () {
  "use strict";

  function createViewer(doc, win) {
    const dialog = doc.createElement("dialog");
    dialog.className = "gisogd-viewer";
    dialog.setAttribute("aria-label", "Просмотр рисунка");
    dialog.setAttribute("aria-describedby", "gisogd-viewer-caption");
    const panel = doc.createElement("div");
    panel.className = "gisogd-viewer__panel";
    const bar = doc.createElement("div");
    bar.className = "gisogd-viewer__bar";
    const label = doc.createElement("span");
    label.textContent = "Просмотр рисунка";
    const closeButton = doc.createElement("button");
    closeButton.type = "button";
    closeButton.className = "gisogd-viewer__close";
    closeButton.textContent = "Закрыть ×";
    closeButton.setAttribute("aria-label", "Закрыть рисунок");
    const image = doc.createElement("img");
    image.className = "gisogd-viewer__image";
    image.alt = "";
    image.draggable = false;
    const caption = doc.createElement("p");
    caption.id = "gisogd-viewer-caption";
    caption.className = "gisogd-viewer__caption";
    bar.append(label, closeButton);
    panel.append(bar, image, caption);
    dialog.append(panel);
    doc.body.append(dialog);

    let state = null;
    const restoreAttribute = (element, value) => {
      if (value === null) element.removeAttribute("style");
      else element.setAttribute("style", value);
    };
    function close(restorePosition = true) {
      if (!state) return;
      const saved = state;
      state = null;
      if (dialog.open) dialog.close();
      restoreAttribute(doc.body, saved.bodyStyle);
      restoreAttribute(doc.documentElement, saved.htmlStyle);
      image.removeAttribute("src");
      image.alt = "";
      caption.textContent = "";
      if (restorePosition) {
        if (saved.trigger.isConnected) saved.trigger.focus({ preventScroll: true });
        win.scrollTo({ left: saved.x, top: saved.y, behavior: "instant" });
      }
    }
    function open(source, trigger) {
      if (state) return;
      state = {
        trigger, x: win.scrollX, y: win.scrollY,
        bodyStyle: doc.body.getAttribute("style"),
        htmlStyle: doc.documentElement.getAttribute("style")
      };
      const gap = Math.max(0, win.innerWidth - doc.documentElement.clientWidth);
      const padding = parseFloat(win.getComputedStyle(doc.body).paddingRight) || 0;
      Object.assign(doc.body.style, {
        position: "fixed", top: `-${state.y}px`, left: `-${state.x}px`,
        width: "100%", overflow: "hidden", boxSizing: "border-box",
        paddingRight: `${padding + gap}px`
      });
      doc.documentElement.style.overflow = "hidden";
      image.src = source.currentSrc || source.src;
      image.alt = source.alt || "Рисунок из руководства";
      const figureCaption = source.closest("figure").querySelector("figcaption");
      caption.textContent = figureCaption ? figureCaption.textContent.trim() : image.alt;
      dialog.showModal();
      closeButton.focus({ preventScroll: true });
    }
    function prepare() {
      // A route change must not restore the previous page's scroll or focus.
      close(false);
      doc.querySelectorAll(".doc-figure img:not(.ui-icon)").forEach((source) => {
        const trigger = source.closest("a") || source;
        trigger.setAttribute("tabindex", "0");
        trigger.setAttribute("role", "button");
        trigger.setAttribute("aria-haspopup", "dialog");
        trigger.setAttribute("aria-label", `Открыть: ${source.alt || "рисунок из руководства"}`);
      });
    }
    function resolveTrigger(target) {
      if (!target || typeof target.closest !== "function") return null;
      const trigger = target.closest('.doc-figure [aria-haspopup="dialog"]');
      if (!trigger) return null;
      const source = trigger.tagName === "IMG" ? trigger : trigger.querySelector("img");
      return source ? { source, trigger } : null;
    }
    function activate(event) {
      if (event.type === "click" && (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)) return;
      const selected = resolveTrigger(event.target);
      if (!selected) return;
      event.preventDefault();
      open(selected.source, selected.trigger);
    }
    doc.addEventListener("click", activate);
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") activate(event);
    });
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
    dialog.addEventListener("close", () => close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target === image) close();
    });
    dialog.addEventListener("keydown", (event) => {
      if (event.key === "Tab") { event.preventDefault(); closeButton.focus({ preventScroll: true }); }
    });
    closeButton.addEventListener("click", () => close());
    win.addEventListener("pagehide", () => close(false));
    return { prepare, open, close, dialog, image, closeButton };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createViewer };
    return;
  }
  let viewer;
  function prepare() {
    if (!viewer) viewer = createViewer(document, window);
    viewer.prepare();
  }
  // Official Material lifecycle: unlike DOMContentLoaded it also covers instant pages.
  if (typeof document$ !== "undefined") document$.subscribe(prepare);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", prepare, { once: true });
  else prepare();
})();
