/**
 * The base map that the place map and the region map share: OpenStreetMap tiles with their
 * required credit (spec 11). This module carries Leaflet, so only lazily loaded modules import it.
 */

import * as L from "leaflet";
import "leaflet/dist/leaflet.css";

// Spec 11: OpenStreetMap tiles need no key, but their attribution is required.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>';
const LEAFLET_CREDIT = '<a href="https://leafletjs.com">Leaflet</a>';
const MAX_TILE_ZOOM = 19;
const WORLD_CENTRE: L.LatLngTuple = [20, 0];
const WORLD_ZOOM = 1;

/**
 * A map of the whole world in `container`, with any extra `options`. The scroll wheel scrolls
 * the page, not the map.
 */
export function createBaseMap(container: HTMLElement, options: L.MapOptions = {}): L.Map {
  const map = L.map(container, {
    center: WORLD_CENTRE,
    zoom: WORLD_ZOOM,
    scrollWheelZoom: false,
    ...options,
  });
  map.attributionControl.setPrefix(LEAFLET_CREDIT);
  L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION, maxZoom: MAX_TILE_ZOOM }).addTo(map);
  return map;
}
