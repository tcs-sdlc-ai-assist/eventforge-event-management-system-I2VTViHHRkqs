(function () {
  "use strict";

  // ============================================================
  // Hamburger Menu Toggle
  // ============================================================
  function initHamburgerMenu() {
    const toggle = document.getElementById("mobile-menu-toggle");
    const menu = document.getElementById("mobile-menu");
    if (!toggle || !menu) return;

    toggle.addEventListener("click", function () {
      menu.classList.toggle("hidden");
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
    });
  }

  // ============================================================
  // Dynamic Ticket Type Rows (Event Create / Edit Form)
  // ============================================================
  function initTicketTypeRows() {
    const container = document.getElementById("ticket-types-container");
    const addBtn = document.getElementById("add-ticket-type-btn");
    if (!container || !addBtn) return;

    let rowIndex = container.querySelectorAll(".ticket-type-row").length;

    function createTicketRow(index) {
      const row = document.createElement("div");
      row.className =
        "ticket-type-row flex flex-wrap items-end gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200";
      row.dataset.index = String(index);

      row.innerHTML =
        '<div class="flex-1 min-w-[140px]">' +
        '  <label class="block text-sm font-medium text-gray-700 mb-1">Ticket Name</label>' +
        '  <input type="text" name="ticket_type_name_' + index + '"' +
        '    class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"' +
        '    placeholder="e.g. General Admission" required />' +
        "</div>" +
        '<div class="w-28">' +
        '  <label class="block text-sm font-medium text-gray-700 mb-1">Price</label>' +
        '  <input type="number" name="ticket_type_price_' + index + '" min="0" value="0"' +
        '    class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"' +
        "    required />" +
        "</div>" +
        '<div class="w-28">' +
        '  <label class="block text-sm font-medium text-gray-700 mb-1">Quantity</label>' +
        '  <input type="number" name="ticket_type_quantity_' + index + '" min="1" value="1"' +
        '    class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"' +
        "    required />" +
        "</div>" +
        '<div class="flex items-end">' +
        '  <button type="button" class="remove-ticket-type-btn inline-flex items-center px-3 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500">' +
        "    &times; Remove" +
        "  </button>" +
        "</div>";

      return row;
    }

    addBtn.addEventListener("click", function () {
      var row = createTicketRow(rowIndex);
      container.appendChild(row);
      rowIndex++;
      updateRemoveButtons();
    });

    container.addEventListener("click", function (e) {
      var btn = e.target.closest(".remove-ticket-type-btn");
      if (!btn) return;
      var row = btn.closest(".ticket-type-row");
      if (row) {
        row.remove();
        updateRemoveButtons();
      }
    });

    function updateRemoveButtons() {
      var rows = container.querySelectorAll(".ticket-type-row");
      var buttons = container.querySelectorAll(".remove-ticket-type-btn");
      buttons.forEach(function (btn) {
        if (rows.length <= 1) {
          btn.disabled = true;
          btn.classList.add("opacity-50", "cursor-not-allowed");
        } else {
          btn.disabled = false;
          btn.classList.remove("opacity-50", "cursor-not-allowed");
        }
      });
    }

    updateRemoveButtons();
  }

  // ============================================================
  // Ticket Type Capacity Validation
  // ============================================================
  function initTicketCapacityValidation() {
    var form = document.getElementById("event-form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      var capacityInput = form.querySelector('[name="total_capacity"]');
      if (!capacityInput) return;

      var totalCapacity = parseInt(capacityInput.value, 10) || 0;
      var container = document.getElementById("ticket-types-container");
      if (!container) return;

      var rows = container.querySelectorAll(".ticket-type-row");
      var ticketSum = 0;
      rows.forEach(function (row) {
        var qtyInput = row.querySelector('input[name^="ticket_type_quantity_"]');
        if (qtyInput) {
          ticketSum += parseInt(qtyInput.value, 10) || 0;
        }
      });

      if (ticketSum > totalCapacity) {
        e.preventDefault();
        showFlashMessage(
          "Sum of ticket quantities (" +
            ticketSum +
            ") exceeds total capacity (" +
            totalCapacity +
            ").",
          "error"
        );
        return false;
      }

      // Validate end > start
      var startInput = form.querySelector('[name="start_datetime"]');
      var endInput = form.querySelector('[name="end_datetime"]');
      if (startInput && endInput) {
        var startDate = new Date(startInput.value);
        var endDate = new Date(endInput.value);
        if (endDate <= startDate) {
          e.preventDefault();
          showFlashMessage("End date/time must be after start date/time.", "error");
          return false;
        }
      }
    });
  }

  // ============================================================
  // RSVP Status Toggle via Fetch API
  // ============================================================
  function initRSVPToggle() {
    var rsvpButtons = document.querySelectorAll("[data-rsvp-status]");
    if (!rsvpButtons.length) return;

    rsvpButtons.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var status = btn.dataset.rsvpStatus;
        var eventId = btn.dataset.eventId;
        if (!status || !eventId) return;

        var csrfToken = getCSRFToken();

        fetch("/events/" + eventId + "/rsvp", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken || "",
          },
          body: "status=" + encodeURIComponent(status),
          credentials: "same-origin",
        })
          .then(function (response) {
            if (!response.ok) {
              return response.json().then(function (data) {
                throw new Error(data.error || data.detail || "RSVP failed");
              });
            }
            return response.json();
          })
          .then(function (data) {
            showFlashMessage(data.message || "RSVP updated!", "success");
            updateRSVPButtons(status);
            if (data.counts) {
              updateRSVPCounts(data.counts);
            }
          })
          .catch(function (err) {
            showFlashMessage(err.message || "Failed to update RSVP.", "error");
          });
      });
    });

    function updateRSVPButtons(activeStatus) {
      rsvpButtons.forEach(function (btn) {
        btn.classList.remove(
          "bg-indigo-600",
          "text-white",
          "bg-yellow-500",
          "bg-green-600",
          "bg-red-500",
          "ring-2",
          "ring-offset-2"
        );
        btn.classList.add("bg-gray-200", "text-gray-700");

        if (btn.dataset.rsvpStatus === activeStatus) {
          btn.classList.remove("bg-gray-200", "text-gray-700");
          var colorMap = {
            going: "bg-green-600",
            maybe: "bg-yellow-500",
            not_going: "bg-red-500",
          };
          btn.classList.add(
            colorMap[activeStatus] || "bg-indigo-600",
            "text-white",
            "ring-2",
            "ring-offset-2"
          );
        }
      });
    }

    function updateRSVPCounts(counts) {
      var goingEl = document.getElementById("rsvp-count-going");
      var maybeEl = document.getElementById("rsvp-count-maybe");
      var notGoingEl = document.getElementById("rsvp-count-not_going");

      if (goingEl && counts.going !== undefined) {
        goingEl.textContent = counts.going;
      }
      if (maybeEl && counts.maybe !== undefined) {
        maybeEl.textContent = counts.maybe;
      }
      if (notGoingEl && counts.not_going !== undefined) {
        notGoingEl.textContent = counts.not_going;
      }
    }
  }

  // ============================================================
  // Check-in Toggle via Fetch API
  // ============================================================
  function initCheckInToggle() {
    var checkInButtons = document.querySelectorAll("[data-checkin-attendee-id]");
    if (!checkInButtons.length) return;

    checkInButtons.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var attendeeId = btn.dataset.checkinAttendeeId;
        var eventId = btn.dataset.checkinEventId;
        if (!attendeeId || !eventId) return;

        var csrfToken = getCSRFToken();

        btn.disabled = true;
        btn.classList.add("opacity-50", "cursor-wait");

        fetch("/events/" + eventId + "/checkin/" + attendeeId, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken || "",
          },
          credentials: "same-origin",
        })
          .then(function (response) {
            if (!response.ok) {
              return response.json().then(function (data) {
                throw new Error(data.error || data.detail || "Check-in failed");
              });
            }
            return response.json();
          })
          .then(function (data) {
            showFlashMessage(data.message || "Attendee checked in!", "success");
            btn.textContent = "Checked In";
            btn.classList.remove("bg-indigo-600", "hover:bg-indigo-700", "opacity-50", "cursor-wait");
            btn.classList.add("bg-green-600", "cursor-default");
            btn.disabled = true;

            var statusEl = document.getElementById("checkin-status-" + attendeeId);
            if (statusEl) {
              statusEl.textContent = "Checked In";
              statusEl.classList.remove("text-gray-500");
              statusEl.classList.add("text-green-600", "font-semibold");
            }
          })
          .catch(function (err) {
            showFlashMessage(err.message || "Failed to check in attendee.", "error");
            btn.disabled = false;
            btn.classList.remove("opacity-50", "cursor-wait");
          });
      });
    });
  }

  // ============================================================
  // Confirmation Dialogs for Delete Actions
  // ============================================================
  function initDeleteConfirmations() {
    var deleteForms = document.querySelectorAll("form[data-confirm]");
    deleteForms.forEach(function (form) {
      form.addEventListener("submit", function (e) {
        var message = form.dataset.confirm || "Are you sure you want to delete this item? This action cannot be undone.";
        if (!window.confirm(message)) {
          e.preventDefault();
        }
      });
    });

    var deleteLinks = document.querySelectorAll("a[data-confirm]");
    deleteLinks.forEach(function (link) {
      link.addEventListener("click", function (e) {
        var message = link.dataset.confirm || "Are you sure? This action cannot be undone.";
        if (!window.confirm(message)) {
          e.preventDefault();
        }
      });
    });
  }

  // ============================================================
  // Form Validation Helpers
  // ============================================================
  function initFormValidation() {
    var forms = document.querySelectorAll("form[data-validate]");
    forms.forEach(function (form) {
      form.addEventListener("submit", function (e) {
        var isValid = true;
        clearValidationErrors(form);

        // Required fields
        var requiredFields = form.querySelectorAll("[required]");
        requiredFields.forEach(function (field) {
          if (!field.value || !field.value.trim()) {
            isValid = false;
            showFieldError(field, "This field is required.");
          }
        });

        // Email validation
        var emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(function (field) {
          if (field.value && !isValidEmail(field.value)) {
            isValid = false;
            showFieldError(field, "Please enter a valid email address.");
          }
        });

        // Password confirmation
        var password = form.querySelector('[name="password"]');
        var confirmPassword = form.querySelector('[name="confirm_password"]');
        if (password && confirmPassword) {
          if (password.value && password.value.length < 6) {
            isValid = false;
            showFieldError(password, "Password must be at least 6 characters.");
          }
          if (password.value !== confirmPassword.value) {
            isValid = false;
            showFieldError(confirmPassword, "Passwords do not match.");
          }
        }

        // Number min validation
        var numberFields = form.querySelectorAll('input[type="number"][min]');
        numberFields.forEach(function (field) {
          var min = parseFloat(field.getAttribute("min"));
          var val = parseFloat(field.value);
          if (field.value && !isNaN(min) && !isNaN(val) && val < min) {
            isValid = false;
            showFieldError(field, "Value must be at least " + min + ".");
          }
        });

        if (!isValid) {
          e.preventDefault();
        }
      });
    });
  }

  function showFieldError(field, message) {
    field.classList.add("border-red-500", "focus:border-red-500", "focus:ring-red-500");
    field.classList.remove("border-gray-300", "focus:border-indigo-500", "focus:ring-indigo-500");

    var existing = field.parentNode.querySelector(".field-error-msg");
    if (existing) {
      existing.textContent = message;
      return;
    }

    var errorEl = document.createElement("p");
    errorEl.className = "field-error-msg text-sm text-red-600 mt-1";
    errorEl.textContent = message;
    field.parentNode.appendChild(errorEl);
  }

  function clearValidationErrors(form) {
    var errorMsgs = form.querySelectorAll(".field-error-msg");
    errorMsgs.forEach(function (el) {
      el.remove();
    });

    var errorFields = form.querySelectorAll(".border-red-500");
    errorFields.forEach(function (field) {
      field.classList.remove("border-red-500", "focus:border-red-500", "focus:ring-red-500");
      field.classList.add("border-gray-300", "focus:border-indigo-500", "focus:ring-indigo-500");
    });
  }

  function isValidEmail(email) {
    var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  // ============================================================
  // Ticket Claim Form
  // ============================================================
  function initTicketClaimForm() {
    var ticketForm = document.getElementById("ticket-claim-form");
    if (!ticketForm) return;

    ticketForm.addEventListener("submit", function (e) {
      e.preventDefault();

      var eventId = ticketForm.dataset.eventId;
      var ticketTypeSelect = ticketForm.querySelector('[name="ticket_type_id"]');
      var quantityInput = ticketForm.querySelector('[name="quantity"]');

      if (!eventId || !ticketTypeSelect || !quantityInput) return;

      var ticketTypeId = ticketTypeSelect.value;
      var quantity = quantityInput.value;

      if (!ticketTypeId) {
        showFlashMessage("Please select a ticket type.", "error");
        return;
      }
      if (!quantity || parseInt(quantity, 10) < 1) {
        showFlashMessage("Please enter a valid quantity.", "error");
        return;
      }

      var submitBtn = ticketForm.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-50", "cursor-wait");
      }

      var csrfToken = getCSRFToken();

      fetch("/events/" + eventId + "/tickets", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": csrfToken || "",
        },
        body:
          "ticket_type_id=" +
          encodeURIComponent(ticketTypeId) +
          "&quantity=" +
          encodeURIComponent(quantity),
        credentials: "same-origin",
      })
        .then(function (response) {
          if (!response.ok) {
            return response.json().then(function (data) {
              throw new Error(data.error || data.detail || "Ticket claim failed");
            });
          }
          return response.json();
        })
        .then(function (data) {
          showFlashMessage(data.message || "Ticket claimed successfully!", "success");
          // Reload to update availability
          setTimeout(function () {
            window.location.reload();
          }, 1200);
        })
        .catch(function (err) {
          showFlashMessage(err.message || "Failed to claim ticket.", "error");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove("opacity-50", "cursor-wait");
          }
        });
    });
  }

  // ============================================================
  // Flash Message Helper
  // ============================================================
  function showFlashMessage(message, type) {
    var container = document.getElementById("flash-messages");
    if (!container) {
      container = document.createElement("div");
      container.id = "flash-messages";
      container.className = "fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm";
      document.body.appendChild(container);
    }

    var colorClasses = {
      success: "bg-green-50 border-green-400 text-green-800",
      error: "bg-red-50 border-red-400 text-red-800",
      warning: "bg-yellow-50 border-yellow-400 text-yellow-800",
      info: "bg-blue-50 border-blue-400 text-blue-800",
    };

    var classes = colorClasses[type] || colorClasses.info;

    var alert = document.createElement("div");
    alert.className =
      "flex items-center justify-between px-4 py-3 rounded-lg border shadow-lg transition-all duration-300 transform translate-x-full " +
      classes;
    alert.setAttribute("role", "alert");

    var textSpan = document.createElement("span");
    textSpan.className = "text-sm font-medium";
    textSpan.textContent = message;

    var closeBtn = document.createElement("button");
    closeBtn.className = "ml-3 text-lg font-bold leading-none opacity-70 hover:opacity-100 focus:outline-none";
    closeBtn.innerHTML = "&times;";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.addEventListener("click", function () {
      dismissFlash(alert);
    });

    alert.appendChild(textSpan);
    alert.appendChild(closeBtn);
    container.appendChild(alert);

    // Animate in
    requestAnimationFrame(function () {
      alert.classList.remove("translate-x-full");
      alert.classList.add("translate-x-0");
    });

    // Auto-dismiss after 5 seconds
    setTimeout(function () {
      dismissFlash(alert);
    }, 5000);
  }

  function dismissFlash(alert) {
    if (!alert || !alert.parentNode) return;
    alert.classList.remove("translate-x-0");
    alert.classList.add("translate-x-full", "opacity-0");
    setTimeout(function () {
      if (alert.parentNode) {
        alert.parentNode.removeChild(alert);
      }
    }, 300);
  }

  // ============================================================
  // CSRF Token Helper
  // ============================================================
  function getCSRFToken() {
    var metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute("content");
    }
    var csrfInput = document.querySelector('input[name="csrf_token"]');
    if (csrfInput) {
      return csrfInput.value;
    }
    return "";
  }

  // ============================================================
  // Auto-dismiss existing flash messages
  // ============================================================
  function initFlashAutoDismiss() {
    var flashMessages = document.querySelectorAll("[data-flash-auto-dismiss]");
    flashMessages.forEach(function (el) {
      var delay = parseInt(el.dataset.flashAutoDismiss, 10) || 5000;
      setTimeout(function () {
        el.classList.add("opacity-0", "transition-opacity", "duration-300");
        setTimeout(function () {
          if (el.parentNode) {
            el.parentNode.removeChild(el);
          }
        }, 300);
      }, delay);
    });
  }

  // ============================================================
  // Search Form Enhancement
  // ============================================================
  function initSearchForm() {
    var searchInput = document.getElementById("event-search-input");
    if (!searchInput) return;

    var debounceTimer = null;
    searchInput.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        var form = searchInput.closest("form");
        if (form) {
          form.submit();
        }
      }, 600);
    });
  }

  // ============================================================
  // Initialize All Modules on DOMContentLoaded
  // ============================================================
  document.addEventListener("DOMContentLoaded", function () {
    initHamburgerMenu();
    initTicketTypeRows();
    initTicketCapacityValidation();
    initRSVPToggle();
    initCheckInToggle();
    initDeleteConfirmations();
    initFormValidation();
    initTicketClaimForm();
    initFlashAutoDismiss();
    initSearchForm();
  });
})();