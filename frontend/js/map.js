/** Leaflet India map with color-coded live AQI markers */
window.AQI_MAP = (function () {
  var map = null;
  var layer = null;
  var markers = {};
  var onSelect = null;

  function init(containerId, selectCallback) {
    onSelect = selectCallback;
    map = L.map(containerId, {
      center: [22.5, 79],
      zoom: 5,
      minZoom: 4,
      maxZoom: 10,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> CARTO',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);

    layer = L.layerGroup().addTo(map);
  }

  function popupHtml(p) {
    return (
      "<strong>" + p.city_name + "</strong>, " + p.state_name +
      "<br/>AQI: <b style='color:" + (p.aqi_color || "#fff") + "'>" + p.aqi_value + "</b> · " + p.aqi_category +
      "<br/><small>" + (p.observed_at || "") + "</small>"
    );
  }

  function setPoints(points, selectedId) {
    if (!layer) return;
    layer.clearLayers();
    markers = {};

    points.forEach(function (p) {
      if (p.latitude == null || p.longitude == null) return;
      var color = p.aqi_color || "#64748b";
      var icon = L.divIcon({
        className: "aqi-marker-wrap",
        html: '<span class="aqi-marker" style="background:' + color + ";color:" + color + '"></span>',
        iconSize: [14, 14],
      });
      var m = L.marker([p.latitude, p.longitude], { icon: icon });
      m.bindPopup(popupHtml(p));
      m.on("click", function () {
        if (onSelect) onSelect(p.city_id);
      });
      if (p.city_id === selectedId) {
        m.openPopup();
      }
      markers[p.city_id] = m;
      layer.addLayer(m);
    });
  }

  function focusCity(cityId) {
    var m = markers[cityId];
    if (m) {
      map.setView(m.getLatLng(), 7, { animate: true });
      m.openPopup();
    }
  }

  return { init: init, setPoints: setPoints, focusCity: focusCity };
})();
