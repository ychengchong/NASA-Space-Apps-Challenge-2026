import * as L from "leaflet";
import { useEffect, useEffectEvent, useRef } from "react";
import type { JSX } from "react";
import { formatCoordinates } from "../format";
import { createBaseMap } from "../leafletBase";
import type { PlaceOnMap } from "../mapCell";
import { placeCellOutline, placesExtent } from "../mapCell";
import { picksMapCentre } from "../mapKeyboard";
import { placeStyle } from "../placeStyles";
import { ShapeSwatch } from "./ShapeSwatch";

// The closest view: a MERRA-2 cell of about 50 km (spec 6) is clearly visible. A 1° cell, or
// several places, zoom out until the outlines fit.
const PLACE_ZOOM = 7;
const FIT_PADDING_PX: L.PointTuple = [32, 32];
const MARKER_SIZE_PX: L.PointTuple = [18, 18];
const LABEL_OFFSET_PX: L.PointTuple = [12, 0];
const CELL_FILL_OPACITY = 0.12;

/** A place to show; `cell` is the grid cell the API analysed, absent before a case runs. */
export interface MapPlace extends PlaceOnMap {
  name: string;
}

interface PlaceMapProps {
  places: readonly MapPlace[];
  /** Called with the point the user clicked, longitude wrapped into -180 to 180. */
  onPick: (point: { lat: number; lon: number }) => void;
}

/**
 * The map: a marker per place and the outline of its grid cell.
 * Clicking the map, or pressing Enter while it has focus, picks a point. This module carries
 * Leaflet, so callers load it with React.lazy. `places` should keep its identity between renders
 * unless it changes.
 */
export default function PlaceMap({ places, onPick }: PlaceMapProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const pick = useEffectEvent((point: L.LatLng) => {
    const wrapped = point.wrap();
    onPick({ lat: wrapped.lat, lon: wrapped.lng });
  });

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;
    const map = createBaseMap(container);
    const layer = L.layerGroup().addTo(map);
    map.on("click", (event: L.LeafletMouseEvent) => pick(event.latlng));
    map.on("keydown", (event: L.LeafletKeyboardEvent) => {
      if (picksMapCentre(event.originalEvent, container)) pick(map.getCenter());
    });
    mapRef.current = map;
    layerRef.current = layer;
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (map === null || layer === null) return;
    layer.clearLayers();
    places.forEach((place, index) => drawPlace(layer, place, index));
    showPlaces(map, places);
  }, [places]);

  return (
    <section className="panel" aria-labelledby="map-heading">
      <h2 id="map-heading">Map</h2>
      <div
        className="place-map"
        ref={containerRef}
        role="region"
        aria-label="Map of the places in this case"
      />
      <p className="panel-note">
        Click the map to pick a point, or search for a place in the case settings. With a keyboard, focus the
        map, move it with the arrow keys and press Enter to pick the point at its centre.
      </p>
      {places.length > 0 ? (
        <ul className="map-places">
          {places.map((place, index) => (
            <li key={index}>
              <ShapeSwatch index={index} /> {placeCaption(place)}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function drawPlace(layer: L.LayerGroup, place: MapPlace, index: number): void {
  const style = placeStyle(index);
  const outline = placeCellOutline(place);
  if (outline !== undefined) {
    L.rectangle(outline, {
      color: style.color,
      weight: 2,
      fillOpacity: CELL_FILL_OPACITY,
      interactive: false,
    }).addTo(layer);
  }
  // Place names are user text, so they go in as text nodes and never as HTML.
  const swatch = document.createElement("span");
  swatch.className = `shape-swatch shape-${style.shape}`;
  swatch.style.setProperty("--place-color", style.color);
  const label = document.createElement("span");
  label.textContent = place.name;
  // Not a tab stop: a marker has no action, and the list under the map names every place.
  L.marker([place.lat, place.lon], {
    icon: L.divIcon({ className: "map-marker", html: swatch, iconSize: MARKER_SIZE_PX }),
    title: place.name,
    keyboard: false,
  })
    .bindTooltip(label, {
      permanent: true,
      direction: "right",
      offset: LABEL_OFFSET_PX,
      className: "map-label",
    })
    .addTo(layer);
}

function showPlaces(map: L.Map, places: readonly MapPlace[]): void {
  const extent = placesExtent(places);
  if (extent === undefined) return;
  // A lone place without a cell has an extent of one point, which Leaflet shows at maxZoom.
  map.fitBounds(extent, { padding: FIT_PADDING_PX, maxZoom: PLACE_ZOOM });
}

function placeCaption(place: MapPlace): string {
  const { cell } = place;
  if (cell === undefined) return `${place.name}: ${formatCoordinates(place.lat, place.lon)}`;
  return (
    `${place.name}: grid cell centred on ${formatCoordinates(cell.lat, cell.lon)}, ` +
    `${cell.height}° by ${cell.width}°. The outline shows the cell the values describe.`
  );
}
