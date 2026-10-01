javascript
const menu = document.getElementById("menu");
const nav = document.getElementById("nav");

menu.addEventListener("click", () => {
  const isOpen = nav.classList.toggle("open");

  menu.setAttribute("aria-expanded", String(isOpen));
});

nav.addEventListener("click", (e) => {
  if (e.target.closest("a")) {
    nav.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
  }
});

addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    nav.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
  }
});

