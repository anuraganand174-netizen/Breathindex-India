/** HTTP client for AQI backend API */
(function (global) {
  function base() {
    var cfg = global.AQI_CONFIG || {};
    return (cfg.API_BASE || "").replace(/\/$/, "");
  }

  function buildUrl(path, params) {
    var baseUrl = base();
    var full = baseUrl ? baseUrl + path : path;
    var url = new URL(full, global.location.origin);
    if (params) {
      Object.keys(params).forEach(function (k) {
        if (params[k] != null && params[k] !== "") url.searchParams.set(k, params[k]);
      });
    }
    return url.toString();
  }

  async function request(path, params) {
    var res = await fetch(buildUrl(path, params), {
      headers: { Accept: "application/json" },
    });
    var body = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(body.error || res.statusText || "Request failed");
    return body;
  }

  global.AQI_API = {
    health: function () { return request("/api/health"); },
    states: function () { return request("/api/states"); },
    cities: function (stateId) { return request("/api/cities", { state_id: stateId }); },
    latest: function (cityId) {
      return request("/api/aqi/latest", { city_id: cityId, live: 1 });
    },
    live: function (cityId, refresh) {
      return request("/api/aqi/live", { city_id: cityId, refresh: refresh ? 1 : 0 });
    },
    liveMap: function (refresh) {
      return request("/api/aqi/live/map", { refresh: refresh ? 1 : 0 });
    },
    history: function (cityId, days) {
      return request("/api/aqi/history", { city_id: cityId, days: days });
    },
    healthImpact: function (aqi) { return request("/api/health-impact", { aqi: aqi }); },
    predict: function (cityId, model, horizon) {
      return request("/api/predict", {
        city_id: cityId,
        model: model,
        horizon: horizon,
      });
    },
  };
})(window);
