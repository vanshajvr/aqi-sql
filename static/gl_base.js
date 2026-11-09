// Shared by the two MapLibre maps (station_map.js and live.js): the vector
// basemap recoloured to the site palette, the default Delhi view, and short
// station names. Loaded before both.
(function () {
  const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
  const DELHI = { center: [77.15, 28.63], zoom: 9.6 };

  // Site palettes (static/style.css), dark and light
  const PALETTE_DARK = {
    land: "#10161e", residential: "#131a23", park: "#122019", water: "#0d2238",
    waterway: "#123050", building: "#18202a",
    roadMotorway: "#4a5563", roadMajor: "#36404c", roadMinor: "#252d37", casing: "#0d1117",
    rail: "#2b333d", boundary: "#4a5563",
    labelMajor: "#c9d1d9", labelMinor: "#8b949e", labelRoad: "#6e7681", halo: "#0d1117",
  };
  const PALETTE_LIGHT = {
    land: "#f3f4f1", residential: "#eceeea", park: "#e1ecd6", water: "#cadcee",
    waterway: "#b3cde6", building: "#e2e2de",
    roadMotorway: "#d3cec6", roadMajor: "#dedbd5", roadMinor: "#e8e6e2", casing: "#f3f4f1",
    rail: "#cfcfcf", boundary: "#9aa0a6",
    labelMajor: "#3d4248", labelMinor: "#626a72", labelRoad: "#80878e", halo: "#ffffff",
  };
  const theme = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark");
  const palette = () => (theme() === "light" ? PALETTE_LIGHT : PALETTE_DARK);

  // Colours for the stations drawn over the basemap, per theme
  function overlay() {
    return theme() === "light"
      ? { label: "#1f2328", halo: "#ffffff", stroke: "#ffffff", strokeHover: "#1f2328", dim: "#d0d7de" }
      : { label: "#f0f6fc", halo: "#0d1117", stroke: "#0d1117", strokeHover: "#ffffff", dim: "#2d333b" };
  }

  const AMBIGUOUS = new Set(["Pusa"]);
  function shortStationName(name) {
    const short = name.replace(/,\s*(New )?Delhi.*$/, "");
    const op = name.match(/-\s*(DPCC|CPCB|IMD)\s*$/);
    return AMBIGUOUS.has(short) && op ? `${short} (${op[1]})` : short;
  }

  // ---------------------------------------------------------------- basemap

  function setPaint(map, id, prop, value) {
    try { map.setPaintProperty(id, prop, value); } catch (e) { /* layer lacks this property */ }
  }

  function recolourBasemap(map) {
    const PALETTE = palette();
    for (const layer of map.getStyle().layers) {
      const id = layer.id;
      if (layer.type === "background") setPaint(map, id, "background-color", PALETTE.land);
      else if (id === "water") setPaint(map, id, "fill-color", PALETTE.water);
      else if (id === "waterway") setPaint(map, id, "line-color", PALETTE.waterway);
      else if (id === "park" || id === "landcover_wood") {
        setPaint(map, id, "fill-color", PALETTE.park);
        setPaint(map, id, "fill-opacity", 0.9);
      } else if (/ice|glacier/.test(id)) map.setLayoutProperty(id, "visibility", "none");
      else if (id === "landuse_residential") setPaint(map, id, "fill-color", PALETTE.residential);
      else if (id === "building") {
        setPaint(map, id, "fill-color", PALETTE.building);
        setPaint(map, id, "fill-outline-color", PALETTE.land);
      } else if (/^aeroway/.test(id)) {
        setPaint(map, id, layer.type === "fill" ? "fill-color" : "line-color", PALETTE.roadMinor);
      } else if (layer.type === "line" && /casing/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.casing);
      } else if (layer.type === "line" && /motorway/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMotorway);
      } else if (layer.type === "line" && /major/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMajor);
      } else if (layer.type === "line" && /minor|pier/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMinor);
      } else if (layer.type === "line" && /path/.test(id)) {
        map.setLayoutProperty(id, "visibility", "none");
      } else if (layer.type === "line" && /railway/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.rail);
      } else if (/^boundary/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.boundary);
      } else if (layer.type === "symbol") {
        if (/shield|airport/.test(id)) {
          map.setLayoutProperty(id, "visibility", "none");
          continue;
        }
        const major = /city|town|state|country/.test(id);
        const road = /highway|waterway|water_name/.test(id);
        setPaint(map, id, "text-color", road ? PALETTE.labelRoad : major ? PALETTE.labelMajor : PALETTE.labelMinor);
        setPaint(map, id, "text-halo-color", PALETTE.halo);
        setPaint(map, id, "text-halo-width", 1.4);
        setPaint(map, id, "text-opacity", major ? 0.85 : 0.65);
      }
    }
  }


  // Re-theme a map when the visitor switches theme: the basemap, then the
  // map's own station layers through restyleOverlay(map, overlay()).
  function followTheme(map, restyleOverlay) {
    // Not gated on "idle": the live map's pulse animation keeps it from ever
    // going idle. Paint changes work once the style itself has loaded.
    const go = () => { recolourBasemap(map); restyleOverlay(overlay()); };
    window.addEventListener("themechange", () => {
      if (map.getStyle()) go(); else map.once("load", go);
    });
  }

  window.GLBase = { BASEMAP_STYLE, DELHI, PALETTE: PALETTE_DARK, shortStationName, recolourBasemap, overlay, followTheme };
})();
