// MediCare+ front-end behaviour (no inline scripts: CSP compliant)
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navToggle");
  if (toggle) toggle.addEventListener("click", () => document.getElementById("navLinks").classList.toggle("open"));

  // Booking form: show consultation fee for the chosen doctor
  const sel = document.getElementById("doctorSelect");
  const fee = document.getElementById("feeOut");
  if (sel && fee) {
    const update = () => {
      const opt = sel.options[sel.selectedIndex];
      fee.textContent = opt && opt.dataset.fee ? "Rs. " + opt.dataset.fee : "—";
    };
    sel.addEventListener("change", update);
    update();
  }

  // Prescription: add another medicine row
  const add = document.getElementById("addRx");
  if (add) add.addEventListener("click", () => {
    const rows = document.getElementById("rxRows");
    const clone = rows.firstElementChild.cloneNode(true);
    clone.querySelectorAll("input").forEach(i => (i.value = ""));
    rows.appendChild(clone);
  });

  // Confirmation for destructive actions
  document.querySelectorAll("form.confirm-form").forEach(f =>
    f.addEventListener("submit", e => { if (!window.confirm(f.dataset.confirm || "Are you sure?")) e.preventDefault(); }));

  document.querySelectorAll(".print-btn").forEach(b => b.addEventListener("click", () => window.print()));

  // Auto-hide flash messages
  setTimeout(() => document.querySelectorAll(".alert-success,.alert-info").forEach(a => a.remove()), 6000);
});
