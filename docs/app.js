(function () {
  "use strict";

  const demo = window.AUTOMATED_STRAIN_RATE_DEMO;
  const tectonics = window.PB2002_MYANMAR;
  if (!demo || !tectonics || !window.L) {
    document.getElementById("map").textContent = "The map data could not be loaded.";
    return;
  }

  const map = L.map("map", { preferCanvas: true, zoomControl: true });
  const imagery = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri World Imagery",
    },
  ).addTo(map);

  const colors = ["#020106", "#180f3d", "#440f76", "#721f81", "#9e2f7f", "#cd4071", "#f1605d", "#fd9668", "#feca8d", "#fcfdbf"];
  const displayMin = demo.metadata.display_min;
  const displayMax = demo.metadata.display_max;
  const colorFor = (value) => {
    const fraction = Math.max(0, Math.min(1, (value - displayMin) / (displayMax - displayMin)));
    return colors[Math.round(fraction * (colors.length - 1))];
  };

  const strain = L.layerGroup();
  const renderer = L.canvas({ padding: 0.5 });
  demo.strain.forEach(([longitude, latitude, value]) => {
    const normalized = Math.max(0, Math.min(1, (value - displayMin) / (displayMax - displayMin)));
    L.circleMarker([latitude, longitude], {
      renderer,
      radius: 7,
      stroke: false,
      fillColor: colorFor(value),
      fillOpacity: 0.05 + 0.83 * Math.pow(normalized, 0.9),
    })
      .bindTooltip(`${value.toFixed(5)} ${demo.metadata.unit}`, { sticky: true })
      .addTo(strain);
  });
  strain.addTo(map);

  const candidateRegions = L.geoJSON(demo.candidate_regions, {
    style: { color: "#4de3d5", weight: 3, fillColor: "#4de3d5", fillOpacity: 0.06 },
    onEachFeature(feature, layer) {
      const properties = feature.properties;
      layer.bindPopup(
        `<strong>Candidate Z${properties.zone_id}</strong><br>` +
          `Maximum strain: ${properties.maximum_strain.toFixed(5)} ${demo.metadata.unit}<br>` +
          `Mean strain: ${properties.mean_strain.toFixed(5)} ${demo.metadata.unit}<br>` +
          `Area: ${properties.area_km2.toLocaleString(undefined, { maximumFractionDigits: 0 })} km²`,
      );
    },
  }).addTo(map);

  const tectonicBoundaries = L.geoJSON(tectonics, {
    style: { color: "#ffd166", weight: 2.25, opacity: 0.95 },
    onEachFeature(feature, layer) {
      layer.bindTooltip(`PB2002 boundary ${feature.properties.Name}`);
    },
  }).addTo(map);

  const earthquakes = L.layerGroup().addTo(map);
  const renderEarthquakes = (minimumMagnitude) => {
    earthquakes.clearLayers();
    demo.earthquakes
      .filter((event) => event.magnitude >= minimumMagnitude)
      .forEach((event) => {
        const marker = L.circleMarker([event.latitude, event.longitude], {
          renderer,
          radius: 4 + event.magnitude * 1.4,
          color: "#f8fafc",
          weight: 2,
          fillColor: "#2563a7",
          fillOpacity: 0.95,
        });
        marker.bindTooltip(`M${event.magnitude.toFixed(1)} · ${event.date}`, {
          permanent: true,
          direction: "right",
          offset: [8, 0],
          className: "event-label",
        });
        marker.bindPopup(
          `<strong>${event.id}</strong><br>` +
            `Magnitude: ${event.magnitude.toFixed(1)}<br>` +
            `Date: ${event.date}<br>` +
            `Depth: ${event.depth_km.toFixed(1)} km`,
        );
        marker.addTo(earthquakes);
      });
  };

  const bounds = L.latLngBounds(demo.bounds);
  const resetView = () => map.fitBounds(bounds, { padding: [18, 18] });
  resetView();
  renderEarthquakes(4.5);

  L.control.layers(
    { "Esri World Imagery": imagery },
    {
      "Numerical strain": strain,
      "Candidate regions": candidateRegions,
      "Earthquakes": earthquakes,
      "PB2002 boundaries": tectonicBoundaries,
    },
    { collapsed: false },
  ).addTo(map);

  const magnitudeFilter = document.getElementById("magnitude-filter");
  const magnitudeValue = document.getElementById("magnitude-value");
  magnitudeFilter.addEventListener("input", () => {
    const minimumMagnitude = Number(magnitudeFilter.value);
    magnitudeValue.value = minimumMagnitude.toFixed(1);
    renderEarthquakes(minimumMagnitude);
  });
  document.getElementById("reset-view").addEventListener("click", resetView);
  document.getElementById("legend-min").textContent = displayMin.toFixed(3);
  document.getElementById("legend-max").textContent = displayMax.toFixed(3);
})();
