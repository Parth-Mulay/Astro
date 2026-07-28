// Horizontal scroll buttons for astrologer carousel (optional enhancement)
document.querySelectorAll("[data-scroll-left]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-scroll-left");
    const el = document.getElementById(id);
    if (el) el.scrollBy({ left: -220, behavior: "smooth" });
  });
});

document.querySelectorAll("[data-scroll-right]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-scroll-right");
    const el = document.getElementById(id);
    if (el) el.scrollBy({ left: 220, behavior: "smooth" });
  });
});
