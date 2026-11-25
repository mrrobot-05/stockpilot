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

  function showSwappedModals() {
    var root = document.getElementById("modal-root");
    if (!root) return;

    var pending = [];
    root.querySelectorAll(".modal").forEach(function (modal) {
      if (!modal.classList.contains("show")) pending.push(modal);
    });
    if (!pending.length) return;

    /* A previous modal may have been replaced without a Bootstrap hide cycle. */
    document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
      backdrop.remove();
    });
    document.body.classList.remove("modal-open");

    pending.forEach(function (modal) {
      if (window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
      } else {
        modal.classList.add("show");
        modal.style.display = "block";
        document.body.classList.add("modal-open");
      }
    });
  }

  function closeModals() {
    document.querySelectorAll("#modal-root .modal").forEach(function (modal) {
      if (window.bootstrap && window.bootstrap.Modal) {
        var instance = window.bootstrap.Modal.getInstance(modal);
        if (instance) {
          instance.hide();
          return;
        }
      }
      modal.classList.remove("show");
      modal.style.display = "none";
    });
    var backdrop = document.querySelector(".modal-backdrop");
    if (backdrop) backdrop.remove();
    document.body.classList.remove("modal-open");
  }

  function onShowToast(event) {
    var detail = event.detail || {};
    if (typeof window.showToast === "function") {
      window.showToast(detail.message || "", detail.type || "info");
    }
  }

  function init() {
    updateToggleButton();
    document.querySelectorAll("#themeToggle").forEach(function (button) {
      button.addEventListener("click", function () {
        setTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    });
    document.body.addEventListener("htmx:afterSwap", showSwappedModals);
    document.body.addEventListener("closeModal", closeModals);
    document.body.addEventListener("showToast", onShowToast);

    /* A create submitted from a detail page has no table to retarget. */
    document.body.addEventListener("htmx:targetError", function (event) {
      var detail = event.detail || {};
      if (detail.target === "#product-table" && window.location.pathname.startsWith("/products/")) {
        window.location.assign("/products");
      }
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
