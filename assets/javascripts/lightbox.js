document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.createElement("div");
  overlay.className = "docs-lightbox";
  overlay.setAttribute("aria-hidden", "true");

  const image = document.createElement("img");
  image.className = "docs-lightbox__image";
  image.alt = "";
  overlay.appendChild(image);
  document.body.appendChild(overlay);

  const close = () => {
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    image.removeAttribute("src");
    image.alt = "";
    document.body.classList.remove("docs-lightbox-open");
  };

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLImageElement)) return;
    if (!target.closest(".md-typeset")) return;
    if (target.classList.contains("ui-icon")) return;

    image.src = target.currentSrc || target.src;
    image.alt = target.alt || "Увеличенное изображение";
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("docs-lightbox-open");
  });

  overlay.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && overlay.classList.contains("is-open")) close();
  });
});
