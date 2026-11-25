/* StockPilot UI helpers: theme persistence and toast notifications. */
(function () {
  "use strict";

  var STORAGE_KEY = "sp-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-bs-theme") === "dark"
      ? "dark"
      : "light";
  }

  function updateToggleButton() {
    var dark = currentTheme() === "dark";
    var icon = dark ? "bi-sun" : "bi-moon-stars";
    var label = dark ? "Switch to light mode" : "Switch to dark mode";
    document.querySelectorAll("#themeToggle").forEach(function (button) {
      button.innerHTML =
        '<i class="bi ' + icon + '" aria-hidden="true"></i>';
      button.setAttribute("aria-label", label);
      button.setAttribute("aria-pressed", String(dark));
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      /* Private browsing can block storage; the toggle still works in this tab. */
    }
    updateToggleButton();
  }

  function init() {
    updateToggleButton();
    document.querySelectorAll("#themeToggle").forEach(function (button) {
      button.addEventListener("click", function () {
        setTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.showToast = function showToast(message, type) {
    var container = document.getElementById("toastContainer");
    if (!container) return;

    var variants = {
      success: { css: "text-bg-success", icon: "bi-check-circle", light: false },
      info: { css: "text-bg-info", icon: "bi-info-circle", light: true },
      warning: { css: "text-bg-warning", icon: "bi-exclamation-triangle", light: true },
      danger: { css: "text-bg-danger", icon: "bi-x-circle", light: false },
      error: { css: "text-bg-danger", icon: "bi-x-circle", light: false },
    };
    var variant = variants[type] || variants.info;

    var toast = document.createElement("div");
    toast.className = "toast align-items-center border-0 " + variant.css;
    toast.setAttribute("role", type === "danger" || type === "error" ? "alert" : "status");
    toast.setAttribute("aria-live", "polite");
    toast.setAttribute("aria-atomic", "true");

    var flex = document.createElement("div");
    flex.className = "d-flex";

    var body = document.createElement("div");
    body.className = "toast-body d-flex align-items-center gap-2";
    var icon = document.createElement("i");
    icon.className = "bi " + variant.icon;
    icon.setAttribute("aria-hidden", "true");
    var text = document.createElement("span");
    text.textContent = String(message);
    body.appendChild(icon);
    body.appendChild(text);

    var close = document.createElement("button");
    close.type = "button";
    close.className =
      "btn-close me-2 m-auto" + (variant.light ? "" : " btn-close-white");
    close.setAttribute("data-bs-dismiss", "toast");
    close.setAttribute("aria-label", "Close notification");

    flex.appendChild(body);
    flex.appendChild(close);
    toast.appendChild(flex);
    container.appendChild(toast);

    if (window.bootstrap && window.bootstrap.Toast) {
      var instance = new window.bootstrap.Toast(toast, { delay: 4000 });
      toast.addEventListener("hidden.bs.toast", function () {
        toast.remove();
      });
      instance.show();
    } else {
      window.setTimeout(function () {
        toast.remove();
      }, 4000);
    }
  };
})();
