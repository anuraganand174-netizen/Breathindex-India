(function () {
  var REFRESH_MS = 10 * 60 * 1000;
  var mapPoints = [];
  var chart = null;
  var selectedCityId = null;

  var stateSelect = document.getElementById("state-select");
  var citySelect = document.getElementById("city-select");
  var daysRange = document.getElementById("days-range");
  var daysLabel = document.getElementById("days-label");
  var apiStatus = document.getElementById("api-status");
  var gaugeProgress = document.getElementById("gauge-progress");

  var AQI_COLORS = {
    good: "#22c55e",
    sat: "#84cc16",
    mod: "#eab308",
    poor: "#f97316",
    vpoor: "#ef4444",
    sev: "#991b1b",
  };

  function aqiColor(aqi) {
    if (aqi <= 50) return AQI_COLORS.good;
    if (aqi <= 100) return AQI_COLORS.sat;
    if (aqi <= 200) return AQI_COLORS.mod;
    if (aqi <= 300) return AQI_COLORS.poor;
    if (aqi <= 400) return AQI_COLORS.vpoor;
    return AQI_COLORS.sev;
  }

  function setStatus(state, text) {
    apiStatus.textContent = text;
    apiStatus.className = "pill " + state;
  }

  function setGauge(aqi) {
    var max = 500;
    var pct = Math.min(1, (aqi || 0) / max);
    var circ = 553;
    gaugeProgress.style.strokeDashoffset = String(circ * (1 - pct));
    gaugeProgress.style.stroke = aqiColor(aqi || 0);
  }

  function updateClock() {
    var el = document.getElementById("live-clock");
    el.textContent = new Date().toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  function renderStats(summary) {
    if (!summary || !summary.national_avg_aqi) return;
    document.getElementById("stat-avg").textContent = summary.national_avg_aqi;
    document.getElementById("stat-avg-cat").textContent = summary.national_avg_category || "";
    document.getElementById("stat-worst").textContent = summary.worst_aqi;
    document.getElementById("stat-worst-sub").textContent = summary.worst_city || "";
    document.getElementById("stat-best").textContent = summary.best_aqi;
    document.getElementById("stat-best-sub").textContent = summary.best_city || "";
    document.getElementById("stat-count").textContent = summary.cities_reporting || "—";
  }

  function renderPollutants(data) {
    var wrap = document.getElementById("pollutant-bars");
    wrap.innerHTML = "";
    var defs = [
      ["PM2.5", data.pm25, 250],
      ["PM10", data.pm10, 430],
      ["NO₂", data.no2, 200],
      ["SO₂", data.so2, 80],
      ["CO", data.co, 10],
      ["O₃", data.o3, 200],
    ];
    defs.forEach(function (d) {
      var val = d[1] != null ? Number(d[1]) : 0;
      var pct = Math.min(100, (val / d[2]) * 100);
      var row = document.createElement("div");
      row.className = "poll-row";
      row.innerHTML =
        "<span>" + d[0] + '</span><div class="bar"><span style="width:' +
        pct + '%;background:' + aqiColor(data.aqi_value || 100) + '"></span></div><span>' +
        (d[1] != null ? Math.round(val * 10) / 10 : "—") + "</span>";
      wrap.appendChild(row);
    });
  }

  function renderRankings(points) {
    var el = document.getElementById("city-rankings");
    var sorted = points.slice().sort(function (a, b) {
      return (b.aqi_value || 0) - (a.aqi_value || 0);
    });
    el.innerHTML = "";
    sorted.slice(0, 24).forEach(function (p) {
      var card = document.createElement("div");
      card.className = "rank-card" + (p.city_id === selectedCityId ? " active" : "");
      card.innerHTML =
        '<div class="name">' + p.city_name + '</div><div class="aqi" style="color:' +
        (p.aqi_color || aqiColor(p.aqi_value)) + '">' + p.aqi_value + "</div>";
      card.addEventListener("click", function () {
        selectCity(p.city_id, true);
      });
      el.appendChild(card);
    });
  }

  function renderCity(data, live) {
    var aqi = data.aqi_value;
    document.getElementById("aqi-value").textContent = aqi ?? "—";
    document.getElementById("aqi-value").style.color = data.aqi_color || aqiColor(aqi);
    document.getElementById("aqi-category").textContent = data.aqi_category || "—";
    document.getElementById("aqi-meta").textContent =
      (data.city_name || "") + ", " + (data.state_name || "") +
      (data.observed_at ? " · " + data.observed_at : "");

    var tag = document.getElementById("data-source");
    tag.textContent = live ? "LIVE" : "CACHED";
    tag.className = "tag" + (live ? "" : " cached");

    setGauge(aqi);
    renderPollutants(data);

    if (aqi != null) {
      AQI_API.healthImpact(aqi).then(function (res) {
        var h = res.data;
        document.getElementById("health-category").textContent = h.category;
        document.getElementById("health-effect").textContent = h.health_effect;
        document.getElementById("health-precautions").textContent = h.precautions;
      }).catch(function () {});
    }
  }

  function buildChart(points) {
    var ctx = document.getElementById("aqi-chart").getContext("2d");
    var labels = points.map(function (p) {
      return (p.timestamp || "").slice(0, 10);
    });
    var vals = points.map(function (p) { return p.aqi_value; });
    var color = aqiColor(vals[vals.length - 1] || 100);

    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "AQI",
          data: vals,
          borderColor: color,
          backgroundColor: color + "33",
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: "#64748b", maxTicksLimit: 8 },
            grid: { color: "rgba(148,163,184,0.08)" },
          },
          y: {
            ticks: { color: "#64748b" },
            grid: { color: "rgba(148,163,184,0.08)" },
            suggestedMin: 0,
          },
        },
      },
    });
  }

  async function loadMap(refresh) {
    setStatus("loading", "Syncing live map…");
    var res = await AQI_API.liveMap(refresh);
    mapPoints = res.data || [];
    AQI_MAP.setPoints(mapPoints, selectedCityId);
    renderStats(res.summary);
    renderRankings(mapPoints);

    var updated = res.updated_at
      ? new Date(res.updated_at).toLocaleString("en-IN")
      : "just now";
    document.getElementById("map-updated").textContent =
      (res.cached ? "Cached · " : "Live · ") + mapPoints.length + " cities · Updated " + updated;
    setStatus("ok", "Live data");
  }

  async function selectCity(cityId, fromMap) {
    selectedCityId = cityId;
    citySelect.value = String(cityId);
    if (fromMap) AQI_MAP.focusCity(cityId);

    var point = mapPoints.find(function (p) { return p.city_id === cityId; });
    if (point) renderCity(point, true);

    try {
      var latest = await AQI_API.latest(cityId);
      renderCity(latest.data, latest.live !== false);
    } catch (e) {
      console.warn(e);
    }

    var days = parseInt(daysRange.value, 10);
    var hist = await AQI_API.history(cityId, days);
    buildChart(hist.data || []);
    renderRankings(mapPoints);
  }

  stateSelect.addEventListener("change", async function () {
    var sid = stateSelect.value;
    if (!sid) return;
    var res = await AQI_API.cities(sid);
    citySelect.innerHTML = '<option value="">Choose city</option>';
    res.data.forEach(function (c) {
      var opt = document.createElement("option");
      opt.value = c.city_id;
      opt.textContent = c.city_name;
      citySelect.appendChild(opt);
    });
  });

  citySelect.addEventListener("change", function () {
    var id = parseInt(citySelect.value, 10);
    if (id) selectCity(id, true);
  });

  daysRange.addEventListener("input", function () {
    daysLabel.textContent = daysRange.value + "d";
    if (selectedCityId) selectCity(selectedCityId, false);
  });

  document.getElementById("predict-btn").addEventListener("click", async function () {
    if (!selectedCityId) {
      document.getElementById("predict-result").textContent = "Select a city first.";
      return;
    }
    var model = document.getElementById("model-select").value;
    var horizon = document.getElementById("horizon-select").value;
    try {
      var res = await AQI_API.predict(selectedCityId, model, horizon);
      document.getElementById("predict-result").textContent = res.ok
        ? "Forecast +" + res.horizon_days + "d: AQI " + res.predicted_aqi + " (now " + res.current_aqi + ")"
        : (res.error || "Failed");
    } catch (e) {
      document.getElementById("predict-result").textContent = e.message;
    }
  });

  document.getElementById("refresh-btn").addEventListener("click", function () {
    loadMap(true).then(function () {
      if (selectedCityId) return selectCity(selectedCityId, false);
    }).catch(function (e) {
      setStatus("err", "Sync failed");
      console.error(e);
    });
  });

  async function init() {
    updateClock();
    setInterval(updateClock, 1000);

    AQI_MAP.init("india-map", function (cityId) {
      selectCity(cityId, false);
    });

    try {
      await AQI_API.health();
    } catch (e) {
      setStatus("err", "API offline");
      document.getElementById("map-updated").textContent =
        "Start backend: python -m api.flask_api";
      return;
    }

    var states = await AQI_API.states();
    stateSelect.innerHTML = '<option value="">Select state</option>';
    states.data.forEach(function (s) {
      var opt = document.createElement("option");
      opt.value = s.state_id;
      opt.textContent = s.state_name;
      stateSelect.appendChild(opt);
    });

    await loadMap(false);

    if (mapPoints.length) {
      await selectCity(mapPoints[0].city_id, false);
    }

    setInterval(function () {
      loadMap(false).catch(console.error);
    }, REFRESH_MS);
  }

  init().catch(function (e) {
    setStatus("err", "Init failed");
    console.error(e);
  });
})();
