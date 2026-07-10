(function () {
  function init() {
    if (typeof io === "undefined") return;
    var badge = document.getElementById("notif-badge");
    if (!badge) return;

    var socket = io();

    socket.on("connect", function () {
      socket.emit("join", {});
      fetchUnreadCount();
    });

    socket.on("new_notification", function (data) {
      if (data.unread_count !== undefined) {
        updateBadge(data.unread_count);
      } else {
        fetchUnreadCount();
      }
      showToast(data);
    });

    function fetchUnreadCount() {
      fetch("/notifications/unread-count")
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.count !== undefined) updateBadge(d.count);
        })
        .catch(function () {});
    }

    function updateBadge(count) {
      if (!badge) return;
      if (count > 0) {
        badge.textContent = count > 99 ? "99+" : count;
        badge.style.display = "inline";
      } else {
        badge.style.display = "none";
      }
    }

    function showToast(data) {
      var container = document.getElementById("toast-container");
      if (!container) return;

      var toast = document.createElement("div");
      toast.className = "notif-toast";

      var iconMap = {
        attendance: "clipboard-check",
        grade: "star",
        internship_offer: "briefcase",
        letter_issued: "file",
        announcement: "bullhorn",
      };
      var icon = iconMap[data.type] || "circle";

      toast.innerHTML =
        '<div class="notif-toast-icon"><i class="fas fa-' +
        icon +
        '"></i></div>' +
        '<div class="notif-toast-body">' +
        '<div class="notif-toast-title">' +
        escapeHtml(data.title || "Notification") +
        "</div>" +
        '<div class="notif-toast-text">' +
        escapeHtml((data.body || "").substring(0, 120)) +
        "</div>" +
        "</div>" +
        '<button class="notif-toast-close">&times;</button>';

      toast.addEventListener("click", function (e) {
        if (e.target.closest(".notif-toast-close")) return;
        if (data.link) window.location.href = data.link;
      });

      toast.querySelector(".notif-toast-close").addEventListener("click", function () {
        toast.remove();
      });

      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      container.appendChild(toast);
      requestAnimationFrame(function () {
        toast.style.opacity = "1";
        toast.style.transform = "translateX(0)";
      });

      setTimeout(function () {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(function () {
          if (toast.parentNode) toast.remove();
        }, 300);
      }, 5000);
    }

    function escapeHtml(str) {
      if (!str) return "";
      var div = document.createElement("div");
      div.appendChild(document.createTextNode(str));
      return div.innerHTML;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
