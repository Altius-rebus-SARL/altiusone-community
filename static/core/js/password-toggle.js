/**
 * Password visibility toggle - Auto-enhances all password inputs.
 * Wraps each <input type="password"> in a Bootstrap input-group
 * and adds an eye/eye-off toggle button.
 */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
      // Skip if already wrapped
      if (input.parentElement.classList.contains("input-group")) return;

      // Create wrapper
      var wrapper = document.createElement("div");
      wrapper.className = "input-group";

      // Insert wrapper before input, then move input inside
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      // Create toggle button
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-outline-secondary";
      btn.tabIndex = -1;
      btn.setAttribute("aria-label", "Toggle password visibility");
      btn.innerHTML = '<i class="ti ti-eye"></i>';
      wrapper.appendChild(btn);

      // Toggle logic
      btn.addEventListener("click", function () {
        var icon = btn.querySelector("i");
        if (input.type === "password") {
          input.type = "text";
          icon.className = "ti ti-eye-off";
        } else {
          input.type = "password";
          icon.className = "ti ti-eye";
        }
      });
    });
  });
})();
