/**
 * API base URL for the dashboard.
 * - Local dev: empty string → same origin as Flask (http://127.0.0.1:5055)
 * - GitHub Pages: set PRODUCTION_API to your Render/Railway HTTPS URL (no trailing slash)
 */
(function () {
  var PRODUCTION_API = "https://YOUR-SERVICE.onrender.com";

  var isLocal =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.protocol === "file:");

  window.AQI_CONFIG = {
    API_BASE: isLocal ? "" : PRODUCTION_API.replace(/\/$/, ""),
  };
})();
