// InternHub small helpers (plain JavaScript, no build step).
document.addEventListener("DOMContentLoaded", function () {
  // Ask before any form that has data-confirm="message" is submitted (e.g. delete).
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  // Auto-submit selects that carry data-autosubmit (status change dropdowns, filters).
  document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () {
      select.form.submit();
    });
  });

  // Fade out success messages after a few seconds.
  document.querySelectorAll(".alert-success").forEach(function (alert) {
    setTimeout(function () {
      alert.classList.remove("show");
      setTimeout(function () { alert.remove(); }, 400);
    }, 5000);
  });
});
