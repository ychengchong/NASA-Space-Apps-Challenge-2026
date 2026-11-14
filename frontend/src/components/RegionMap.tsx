import * as L from "leaflet";
import { useEffect, useEffectEvent, useRef } from "react";
import type { JSX } from "react";
import type { Box, MapCell, TrendMap, VariableSummary } from "../api";
import { slopeColour } from "../colourScale";
import { formatCoordinates, formatPValue, formatRatePerDecade } from "../format";
import { createBaseMap } from "../leafletBase";
import type { Corner } from "../mapCell";
import { boxCorners, boxFromDrag, cellBounds, gridSteps } from "../regionBox";
import type { LatLon } from "../regionBox";

// The no-result hatch is an SVG pattern in this component's markup; Leaflet's own SVG layer
// refers to it by id, so it must be unique on the page.
const NO_RESULT_PATTERN_ID = "region-no-result-hatch";
const NO_RESULT_FILL = `url(#${NO_RESULT_PATTERN_ID})`;
const INK = "#1d232b";
const SURFACE = "#ffffff";
const HATCH_LINE = "#8a949f";
// The tiles show through a little, so coasts stay visible under the cells.
const CELL_FILL_OPACITY = 0.8;
// Cells meet without edges, so the colours read as one field; a hovered cell gets an outline.
const CELL_HOVER_WEIGHT = 2;
// The mark of a significant cell: a dark dot with a white ring, readable on every fill and small
// enough to leave the cell's colour visible around it.
const MARK_RADIUS_PX = 2;
const MARK_RING_WEIGHT = 1;
// Quarter zoom steps let a box fill the map, so its cells are drawn as large as they fit.
const ZOOM_SNAP = 0.25;
const BOX_STYLE: L.PolylineOptions = {
  color: INK,
  weight: 2,
  dashArray: "6 4",
  fill: false,
  interactive: false,
};
const DRAW_STYLE: L.PolylineOptions = { color: INK, weight: 2, fillOpacity: 0.08, interactive: false };
const FIT_PADDING_PX: L.PointTuple = [24, 24];
// Styles the map for drawing: a crosshair, and cells that let presses through to the map.
const DRAWING_CLASS = "is-drawing";
// A press that moves less than this is a click, not a drawn box.
const MIN_DRAG_PX = 6;

interface RegionMapProps {
  /** The box asked for, drawn as a dashed outline; null before a map is set up. */
  box: Box | null;
  /** The cells to draw; null while there is no map. */
  trendMap: TrendMap | null;
  /** The colour scale runs from -scaleLimit to +scaleLimit. */
  scaleLimit: number;
  /** While true, dragging on the map draws a box instead of moving the map. */
  drawing: boolean;
  onBoxDrawn: (box: Box) => void;
  onOpenCell: (cell: MapCell) => void;
}

/**
 * The region map (spec 7, "Region view"): each grid cell is a rectangle coloured by its rate,
 * hatched when it has no result, with a dot on each cell that passes the map's stricter test.
 * Clicking a cell opens it as a case. This module carries Leaflet, so callers load it lazily.
 */
export default function RegionMap({
  box,
  trendMap,
  scaleLimit,
  drawing,
  onBoxDrawn,
  onOpenCell,
}: RegionMapProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const cellLayerRef = useRef<L.LayerGroup | null>(null);
  const boxLayerRef = useRef<L.LayerGroup | null>(null);
  const openCell = useEffectEvent((cell: MapCell) => onOpenCell(cell));
  const finishDrawing = useEffectEvent((drawn: Box) => onBoxDrawn(drawn));

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;
    const map = createBaseMap(container, { zoomSnap: ZOOM_SNAP });
    cellLayerRef.current = L.layerGroup().addTo(map);
    boxLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      cellLayerRef.current = null;
      boxLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const layer = cellLayerRef.current;
    if (layer === null) return;
    layer.clearLayers();
    if (trendMap !== null) drawCells(layer, trendMap, scaleLimit, openCell);
  }, [trendMap, scaleLimit]);

  const south = box?.south;
  const west = box?.west;
  const north = box?.north;
  const east = box?.east;
  useEffect(() => {
    const map = mapRef.current;
    const layer = boxLayerRef.current;
    if (map === null || layer === null) return;
    layer.clearLayers();
    if (south === undefined || west === undefined || north === undefined || east === undefined) return;
    const corners = boxCorners({ south, west, north, east });
    L.rectangle(corners, BOX_STYLE).addTo(layer);
    // A new box is a new area, so the map jumps there rather than flying.
    map.fitBounds(corners, { padding: FIT_PADDING_PX, animate: false });
  }, [south, west, north, east]);

  useEffect(() => {
    const map = mapRef.current;
    if (!drawing || map === null) return;
    return startDrawing(map, finishDrawing);
  }, [drawing]);

  return (
    <>
      <svg className="svg-defs" aria-hidden="true" focusable="false">
        <defs>
          <pattern
            id={NO_RESULT_PATTERN_ID}
            patternUnits="userSpaceOnUse"
            width="6"
            height="6"
            patternTransform="rotate(45)"
          >
            <rect width="6" height="6" fill={SURFACE} />
            <line x1="0" y1="0" x2="0" y2="6" stroke={HATCH_LINE} strokeWidth="2" />
          </pattern>
        </defs>
      </svg>
      <div
        className="place-map region-map"
        ref={containerRef}
        role="region"
        aria-label="Map of the trend in each grid cell. The evidence lists every cell as a table."
      />
    </>
  );
}

function drawCells(
  layer: L.LayerGroup,
  trendMap: TrendMap,
  limit: number,
  onOpen: (cell: MapCell) => void,
): void {
  const steps = gridSteps(trendMap.cells);
  for (const cell of trendMap.cells) {
    const style: L.PathOptions = {
      stroke: false,
      color: INK,
      weight: CELL_HOVER_WEIGHT,
      fillColor: cell.sen_slope === null ? NO_RESULT_FILL : slopeColour(cell.sen_slope, limit),
      fillOpacity: CELL_FILL_OPACITY,
    };
    const rectangle = L.rectangle(cellBounds(cell, steps), style);
    rectangle.bindTooltip(cellTooltip(cell, trendMap.variable), { sticky: true, direction: "top" });
    rectangle.on("click", () => onOpen(cell));
    rectangle.on("mouseover", () => rectangle.setStyle({ stroke: true }));
    rectangle.on("mouseout", () => rectangle.setStyle({ stroke: false }));
    rectangle.addTo(layer);
  }
  // The marks go on top of every cell, and let clicks through to the cell below.
  for (const cell of trendMap.cells) {
    if (!cell.significant) continue;
    L.circleMarker([cell.lat, cell.lon], {
      radius: MARK_RADIUS_PX,
      color: SURFACE,
      weight: MARK_RING_WEIGHT,
      fillColor: INK,
      fillOpacity: 1,
      interactive: false,
    }).addTo(layer);
  }
}

/** The cell's numbers as text nodes, so nothing in them is read as HTML. */
function cellTooltip(cell: MapCell, variable: VariableSummary): HTMLElement {
  const lines = [formatCoordinates(cell.lat, cell.lon)];
  if (cell.sen_slope === null || cell.mk_p === null) {
    lines.push("No result: too few complete years to test.");
  } else {
    lines.push(formatRatePerDecade(cell.sen_slope, variable), pValueText(cell.mk_p));
    if (cell.significant) lines.push("Marked: passes the map's stricter test.");
  }
  lines.push("Click to open this cell as a case.");
  const tooltip = document.createElement("div");
  for (const line of lines) {
    const row = document.createElement("div");
    row.textContent = line;
    tooltip.append(row);
  }
  return tooltip;
}

/** "p = 0.012", or "p < 0.001" for a p-value below what is printed. */
function pValueText(p: number): string {
  const text = formatPValue(p);
  return text.startsWith("<") ? `p ${text}` : `p = ${text}`;
}

/**
 * Lets a drag on the map draw a box, shown snapped to whole degrees as it grows. Returns the
 * function that ends drawing and gives the map back its dragging.
 */
function startDrawing(map: L.Map, onDrawn: (box: Box) => void): () => void {
  // Leaflet owns the container's classes, so the drawing class is set here, not by React.
  const container = map.getContainer();
  container.classList.add(DRAWING_CLASS);
  map.dragging.disable();
  map.boxZoom.disable();
  map.doubleClickZoom.disable();
  let start: L.LatLng | null = null;
  let preview: L.Rectangle | null = null;

  const corners = (from: L.LatLng, to: L.LatLng): [Corner, Corner] =>
    boxCorners(boxFromDrag(wrapped(from), wrapped(to)));
  const down = (event: L.LeafletMouseEvent): void => {
    start = event.latlng;
    preview?.remove();
    preview = L.rectangle(corners(start, start), DRAW_STYLE).addTo(map);
  };
  const move = (event: L.LeafletMouseEvent): void => {
    if (start !== null) preview?.setBounds(L.latLngBounds(corners(start, event.latlng)));
  };
  const up = (event: L.LeafletMouseEvent): void => {
    if (start === null) return;
    const from = start;
    start = null;
    preview?.remove();
    preview = null;
    if (map.latLngToContainerPoint(from).distanceTo(event.containerPoint) < MIN_DRAG_PX) return;
    onDrawn(boxFromDrag(wrapped(from), wrapped(event.latlng)));
  };

  map.on("mousedown", down);
  map.on("mousemove", move);
  map.on("mouseup", up);
  return () => {
    map.off("mousedown", down);
    map.off("mousemove", move);
    map.off("mouseup", up);
    preview?.remove();
    map.dragging.enable();
    map.boxZoom.enable();
    map.doubleClickZoom.enable();
    container.classList.remove(DRAWING_CLASS);
  };
}

function wrapped(point: L.LatLng): LatLon {
  const inside = point.wrap();
  return { lat: inside.lat, lon: inside.lng };
}
