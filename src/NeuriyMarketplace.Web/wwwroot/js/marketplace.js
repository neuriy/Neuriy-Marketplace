(() => {
  const menus = document.querySelectorAll("[data-user-menu]");
  menus.forEach((menu) => {
    const toggle = menu.querySelector("[data-user-menu-toggle]");
    const panel = menu.querySelector("[data-user-menu-panel]");
    if (!toggle || !panel) return;

    const close = () => {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
    };

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = panel.hidden;
      document.querySelectorAll("[data-user-menu-panel]").forEach((other) => {
        other.hidden = true;
      });
      document.querySelectorAll("[data-user-menu]").forEach((other) => {
        other.classList.remove("is-open");
        const btn = other.querySelector("[data-user-menu-toggle]");
        if (btn) btn.setAttribute("aria-expanded", "false");
      });
      if (open) {
        panel.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        menu.classList.add("is-open");
      }
    });

    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) close();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  });

  // Subtle entrance for store hero
  const hero = document.querySelector(".store-hero");
  if (hero) {
    requestAnimationFrame(() => hero.classList.add("is-ready"));
  }
})();
