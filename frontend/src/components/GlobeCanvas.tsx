import { GPUInitializationError, Map as MapLibreMap, Marker, Popup, setWorkerUrl } from "maplibre-gl";
import type { GeoJSONSource, LngLat, MapMouseEvent, MapTouchEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useEffectEvent, useRef } from "react";
import type { JSX, RefObject } from "react";
import type { Box, MapCell, TrendMap, VariableSummary } from "../api";
import { cellTooltipLines } from "../cellTooltip";
import { cardPlaceIndex } from "../examplePins";
import type { ExampleLink, ExampleListeners, ExamplePin } from "../examplePins";
import type { GlobeHandle } from "../globeContext";
import {
  boxCentre,
  boxFeature,
  collection,
  earthDiscRadius,
  earthFacing,
  earthZoom,
  exampleLinkFeatures,
  isInView,
  placeCellFeatures,
  placesCentre,
  regionCellFeatures,
  regionMarkFeatures,
  ringFits,
  stagePadding,
} from "../globeGeometry";
import type { Size } from "../globeGeometry";
import { GLOBE_STYLE, HATCH_IMAGE, LAYER, NO_CELL, SEA_IMAGE, SOURCE } from "../globeStyle";
import type { Corner, MapPlace } from "../mapCell";
import { placesExtent } from "../mapCell";
import { picksMapCentre } from "../mapKeyboard";
import { placeStyle } from "../placeStyles";
import { boxCorners, boxFromDrag } from "../regionBox";
import type { LatLon } from "../regionBox";

// Vite serves the worker as a file of its own; MapLibre would otherwise look for it beside the
// bundled chunk, where it is not.
setWorkerUrl(workerUrl);

// Where the whole Earth faces when there is no place to show.
const HOME_CENTRE: LatLon = { lat: 18, lon: 15 };
// The closest view: a MERRA-2 cell of about 50 km (spec 6) is clearly visible. A 1° cell, or
// several places, pull back until the outlines fit.
const CELL_ZOOM = 6;
const MIN_ZOOM = -1;
const MAX_ZOOM = 9;
const FIT_PADDING_PX = 48;
const FLIGHT_MS = 1800;
const ZOOM_STEP_MS = 300;
// The idle turn of the Earth: one step of the turn, repeated until the user touches the globe.
const SPIN_STEP_DEGREES = 30;
const SPIN_STEP_MS = 15000;
// How long the idle turn waits before it goes on, once no example is singled out any more.
const SPIN_RESUME_MS = 4000;
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
// A press that moves less than this is a click, not a drawn box.
const MIN_DRAG_PX = 6;
// A click this far from where its coordinates are drawn missed the Earth and landed in space.
const SURFACE_TOLERANCE_PX = 2;
// Styles the globe for drawing: a crosshair instead of the grab hand.
const DRAWING_CLASS = "is-drawing";
// Fades the Earth in (styles.css) once its first tiles are drawn, or after this long without
// them, so a slow connection still shows the bare globe rather than nothing.
const READY_CLASS = "is-ready";
const FIRST_PAINT_WAIT_MS = 4000;
// The foot of the stage holds a view's caption or key (GlobeStage). A view that fills the stage
// stays this far above it.
const NOTE_SELECTOR = ".stage-note";
const NOTE_GAP_PX = 12;
// The ring of degree marks round the whole Earth (GlobeStage), which takes the radius of the
// Earth's disc from this custom property (styles.css).
const RING_SELECTOR = ".stage-ring";
const RING_RADIUS_PROPERTY = "--earth-radius";
// Marks the pins of the example the user has singled out (styles.css, .example-pin).
const ACTIVE_PIN_CLASS = "is-active";
const TOOLTIP_OFFSET_PX = 12;
const CANVAS_LABEL =
  "Globe. The arrow keys turn it, plus and minus zoom, and Enter picks the point at its centre.";

// The fill of a cell without a result: diagonal lines of ink on the paper of the land.
const HATCH_SIZE_PX = 8;
const HATCH_LINE_PX = 2;
const HATCH_LINE_RGBA = [107, 88, 70, 255] as const;
const HATCH_GROUND_RGBA = [239, 230, 207, 255] as const;

// The sea's engraving: one fine line, then the sea's own paper, repeated down the map. The lines
// follow the parallels, so they stay still while the Earth turns.
const SEA_LINE_SPACING_PX = 4;
const SEA_TILE_WIDTH_PX = 8;
const SEA_LINE_RGBA = [191, 177, 146, 255] as const;
const SEA_GROUND_RGBA = [224, 213, 184, 255] as const;

/** Where the camera sits: on the whole Earth facing a point, or on an area that fills the stage. */
type View =
  | { kind: "earth"; centre: LatLon | null; spin: boolean }
  | { kind: "area"; corners: [Corner, Corner]; maxZoom?: number };

type PointerEvent = MapMouseEvent | MapTouchEvent;

/** Drives the MapLibre globe; the rest of the app reaches it as a `GlobeHandle`. */
class Globe implements GlobeHandle {
  private readonly map: MapLibreMap;
  private readonly stage: HTMLElement;
  private readonly tooltip: Popup;
  private readonly stageObserver: ResizeObserver;
  private readonly note: HTMLElement | null;
  private readonly noteObserver: ResizeObserver;
  private readonly ring: HTMLElement | null;
  // The radius the ring was last drawn at, so a turning Earth does not rewrite it on every frame.
  private ringRadius = "";
  private readonly revealTimer: number;
  private markers: Marker[] = [];
  private pickedMarker: Marker | null = null;
  private examples: { pin: ExamplePin; markers: Marker[] }[] = [];
  private exampleLink: ExampleLink | null = null;
  private places: readonly MapPlace[] = [];
  // The points of the places the view last turned to; undefined while no place is shown.
  private shownPlaces: string | undefined = undefined;
  private cells: readonly MapCell[] = [];
  private variable: VariableSummary | null = null;
  // The box the view last moved to; undefined while no region map is shown.
  private shownBox: string | null | undefined = undefined;
  private box: Box | null = null;
  private pickHandler: ((point: LatLon) => void) | null = null;
  private cellHandler: ((cell: MapCell) => void) | null = null;
  private stopDrawing: (() => void) | null = null;
  private view: View = { kind: "earth", centre: null, spin: true };
  private spinning = false;
  // True while an example that is or was singled out holds up the idle turn, which goes on after it.
  private spinHeld = false;
  private spinTimer: number | undefined = undefined;
  // True once the user has moved the camera, so a resize leaves their view alone.
  private movedByUser = false;
  // True once the map is gone; a view that still holds the handle may then tidy up after itself.
  private removed = false;

  /** Throws `GPUInitializationError` when the browser cannot give the map a WebGL canvas. */
  constructor(container: HTMLElement, stage: HTMLElement) {
    this.stage = stage;
    this.map = new MapLibreMap({
      container,
      style: GLOBE_STYLE,
      center: [HOME_CENTRE.lon, HOME_CENTRE.lat],
      zoom: earthZoom(stageSize(stage), HOME_CENTRE.lat),
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      // The stage shows the credit itself, where a phone's layout cannot cover it.
      attributionControl: false,
      // North stays up and the view stays overhead, so a cell is always a plain rectangle.
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
    });
    this.map.touchZoomRotate.disableRotation();
    this.map.keyboard.disableRotation();
    this.map.setPadding(this.padding());
    this.syncGestures();
    const reveal = (): void => container.classList.add(READY_CLASS);
    void this.map.once("load").then(reveal);
    this.revealTimer = window.setTimeout(reveal, FIRST_PAINT_WAIT_MS);
    this.tooltip = new Popup({
      closeButton: false,
      closeOnClick: false,
      focusAfterOpen: false,
      offset: TOOLTIP_OFFSET_PX,
      className: "globe-tooltip",
    });

    this.map.on("styleimagemissing", (event) => {
      if (this.map.hasImage(event.id)) return;
      if (event.id === HATCH_IMAGE) this.map.addImage(HATCH_IMAGE, hatchImage());
      if (event.id === SEA_IMAGE) this.map.addImage(SEA_IMAGE, seaImage());
    });
    this.map.on("click", (event) => this.handleClick(event));
    this.map.on("mousemove", (event) => this.handleHover(event));
    this.map.on("mouseout", () => this.endHover());
    this.map.on("moveend", () => this.continueSpin());
    this.map.on("move", () => {
      this.drawRing();
      this.reportExample();
    });
    for (const gesture of ["mousedown", "touchstart", "wheel"] as const) {
      this.map.on(gesture, () => this.takeOver());
    }
    const canvas = this.map.getCanvas();
    canvas.setAttribute("aria-label", CANVAS_LABEL);
    canvas.addEventListener("keydown", (event) => {
      this.takeOver();
      if (this.pickHandler !== null && picksMapCentre(event, canvas)) this.pick(this.map.getCenter());
    });
    this.stageObserver = new ResizeObserver(() => this.fitStage());
    this.stageObserver.observe(stage);
    this.note = stage.querySelector<HTMLElement>(NOTE_SELECTOR);
    this.noteObserver = new ResizeObserver(() => this.keepClearOfNote());
    if (this.note !== null) this.noteObserver.observe(this.note);
    this.ring = stage.querySelector<HTMLElement>(RING_SELECTOR);
    this.drawRing();
    window.addEventListener("resize", this.fitStage);
  }

  /**
   * Calls `onLoaded` once the style is in place, which is when the globe can take data. Call it
   * right after the constructor: MapLibre reads the style a moment later, and says so only once.
   */
  whenLoaded(onLoaded: () => void): void {
    void this.map.once("style.load").then(onLoaded);
  }

  remove(): void {
    window.clearTimeout(this.revealTimer);
    window.clearTimeout(this.spinTimer);
    window.removeEventListener("resize", this.fitStage);
    this.stageObserver.disconnect();
    this.noteObserver.disconnect();
    this.setDrawHandler(null);
    this.removed = true;
    this.map.remove();
  }

  showPlaces(places: readonly MapPlace[]): void {
    this.places = places;
    this.setData(SOURCE.placeCells, placeCellFeatures(places));
    for (const marker of this.markers) marker.remove();
    this.markers = places.map((place, index) =>
      new Marker({
        element: markerElement(place.name, index),
        opacityWhenCovered: "0",
        subpixelPositioning: true,
      })
        .setLngLat([place.lon, place.lat])
        .addTo(this.map),
    );
    // The same places with their cells filled in, as when a case finishes loading, are already
    // in view; the Earth turns only to face places it is not facing yet.
    const points = places.map((place) => `${place.lat},${place.lon}`).join(";");
    if (points === this.shownPlaces) return;
    this.shownPlaces = points;
    const centre = placesCentre(places);
    this.moveTo({ kind: "earth", centre: centre ?? null, spin: centre === undefined });
  }

  clearPlaces(): void {
    this.places = [];
    this.shownPlaces = undefined;
    this.setData(SOURCE.placeCells, collection([]));
    for (const marker of this.markers) marker.remove();
    this.markers = [];
  }

  showPickedPoint(point: LatLon | null): void {
    this.pickedMarker?.remove();
    this.pickedMarker =
      point === null
        ? null
        : new Marker({ element: pickedPointElement(), opacityWhenCovered: "0" })
            .setLngLat([point.lon, point.lat])
            .addTo(this.map);
  }

  showExamples(pins: readonly ExamplePin[], listeners: ExampleListeners): void {
    for (const example of this.examples) for (const marker of example.markers) marker.remove();
    this.exampleLink = null;
    // With the pins gone, the view that showed them is over, and so is the turn they held up.
    if (pins.length === 0) this.forgetSpin();
    this.setData(SOURCE.exampleLinks, exampleLinkFeatures(pins));
    this.examples = pins.map((pin) => ({
      pin,
      markers: pin.places.map((place, index) => {
        // A pin on the far side of the Earth is not drawn, and must not be reached through it.
        const whenSeen = (act: () => void) => (): void => {
          if (this.sees(place)) act();
        };
        return new Marker({
          element: examplePinElement(pin, place, index === cardPlaceIndex(pin), {
            onOpen: whenSeen(() => listeners.onOpen(pin)),
            onEnter: whenSeen(() => listeners.onPoint(pin)),
            onLeave: () => listeners.onPoint(null),
          }),
          opacityWhenCovered: "0",
          subpixelPositioning: true,
        })
          .setLngLat([place.lon, place.lat])
          .addTo(this.map);
      }),
    }));
  }

  linkExample(link: ExampleLink | null): void {
    this.exampleLink = link;
    for (const { pin, markers } of this.examples) {
      for (const marker of markers) {
        marker.getElement().classList.toggle(ACTIVE_PIN_CLASS, pin.number === link?.number);
      }
    }
    window.clearTimeout(this.spinTimer);
    const linked = this.linkedExample();
    if (link === null || linked === undefined) {
      if (this.spinHeld) this.spinTimer = window.setTimeout(() => this.resumeSpin(), SPIN_RESUME_MS);
      return;
    }
    // Spec 3: an example that is singled out holds up the idle turn; it does not end it.
    const held = this.spinning || this.spinHeld;
    const centre = link.turn ? placesCentre(linked.places) : undefined;
    if (centre === undefined) this.stopSpin();
    else this.moveTo({ kind: "earth", centre, spin: false });
    this.spinHeld = held;
    this.reportExample();
  }

  zoomToCells(): void {
    const corners = placesExtent(this.places);
    if (corners !== undefined) this.moveTo({ kind: "area", corners, maxZoom: CELL_ZOOM });
  }

  setPickHandler(handler: ((point: LatLon) => void) | null): void {
    this.pickHandler = handler;
  }

  showRegion(box: Box | null, trendMap: TrendMap | null, scaleLimit: number): void {
    this.box = box;
    this.cells = trendMap?.cells ?? [];
    this.variable = trendMap?.variable ?? null;
    this.setData(
      SOURCE.cells,
      box === null ? collection([]) : regionCellFeatures(this.cells, scaleLimit, box),
    );
    this.setData(SOURCE.cellMarks, regionMarkFeatures(this.cells));
    this.setData(SOURCE.box, collection(box === null ? [] : [boxFeature(box)]));
    this.endHover();
    const boxKey = box === null ? null : `${box.south},${box.west},${box.north},${box.east}`;
    if (boxKey === this.shownBox) return;
    this.shownBox = boxKey;
    this.moveTo(
      box === null
        ? { kind: "earth", centre: null, spin: false }
        : { kind: "area", corners: boxCorners(box) },
    );
  }

  clearRegion(): void {
    this.box = null;
    this.cells = [];
    this.variable = null;
    this.shownBox = undefined;
    for (const source of [SOURCE.cells, SOURCE.cellMarks, SOURCE.box]) this.setData(source, collection([]));
    this.endHover();
  }

  setCellHandler(handler: ((cell: MapCell) => void) | null): void {
    this.cellHandler = handler;
  }

  setDrawHandler(handler: ((box: Box) => void) | null): void {
    this.stopDrawing?.();
    this.stopDrawing = handler === null ? null : this.startDrawing(handler);
    this.syncGestures();
  }

  zoomBy(levels: number): void {
    this.takeOver();
    this.map.easeTo({ zoom: this.map.getZoom() + levels, duration: ZOOM_STEP_MS });
  }

  showEarth(): void {
    const centre = placesCentre(this.places) ?? (this.box === null ? null : boxCentre(this.box));
    this.moveTo({ kind: "earth", centre, spin: false });
  }

  /** Moves the camera to `view` and remembers it, so a resize can restore it. */
  private moveTo(view: View): void {
    this.forgetSpin();
    this.view = view;
    this.movedByUser = false;
    this.applyView(FLIGHT_MS);
  }

  private applyView(duration: number): void {
    const { view } = this;
    this.spinning = false;
    if (view.kind === "area") {
      const [[south, west], [north, east]] = view.corners;
      this.map.fitBounds(
        [
          [west, south],
          [east, north],
        ],
        {
          padding: {
            top: FIT_PADDING_PX,
            right: FIT_PADDING_PX,
            bottom: this.footRoom(),
            left: FIT_PADDING_PX,
          },
          maxZoom: view.maxZoom ?? MAX_ZOOM,
          linear: true,
          duration,
        },
      );
      return;
    }
    // With no point to face, the Earth keeps the side it shows and levels out.
    const centre = earthFacing(view.centre ?? { lat: HOME_CENTRE.lat, lon: this.map.getCenter().lng });
    this.spinning = view.spin && !this.spinHeld && !window.matchMedia(REDUCED_MOTION_QUERY).matches;
    this.map.easeTo({
      center: [centre.lon, centre.lat],
      zoom: earthZoom(stageSize(this.stage), centre.lat),
      duration,
    });
  }

  /** The next step of the idle turn, started each time the last one ends. */
  private continueSpin(): void {
    if (!this.spinning) return;
    const centre = this.map.getCenter();
    this.map.easeTo({
      center: [centre.lng + SPIN_STEP_DEGREES, centre.lat],
      duration: SPIN_STEP_MS,
      easing: (progress) => progress,
    });
  }

  /** The user has touched the globe: the idle turn ends, and their view is theirs to keep. */
  private takeOver(): void {
    this.movedByUser = true;
    this.forgetSpin();
    this.stopSpin();
  }

  private stopSpin(): void {
    if (!this.spinning) return;
    this.spinning = false;
    this.map.stop();
  }

  /** The idle turn that an example held up goes on, from the side of the Earth now in view. */
  private resumeSpin(): void {
    this.moveTo({ kind: "earth", centre: null, spin: true });
  }

  /** The idle turn that an example held up does not go on. */
  private forgetSpin(): void {
    window.clearTimeout(this.spinTimer);
    this.spinHeld = false;
  }

  // An arrow function, so it can be given to and taken from the window's resize event.
  private readonly fitStage = (): void => {
    this.map.setPadding(this.padding());
    this.syncGestures();
    if (!this.movedByUser) this.applyView(0);
    this.drawRing();
  };

  private linkedExample(): ExamplePin | undefined {
    const { exampleLink } = this;
    if (exampleLink === null) return undefined;
    return this.examples.find((example) => example.pin.number === exampleLink.number)?.pin;
  }

  /** Tells the example that is singled out where its pins are now. */
  private reportExample(): void {
    const linked = this.linkedExample();
    if (linked === undefined) return;
    this.exampleLink?.onMove(
      linked.places.map((place) => {
        if (!this.sees(place)) return null;
        const { x, y } = this.map.project([place.lon, place.lat]);
        return { x, y };
      }),
    );
  }

  /** True when the point is on the side of the Earth the camera sees. */
  private sees(point: LatLon): boolean {
    const { map } = this;
    const centre = map.getCenter();
    return isInView(
      { lat: centre.lat, lon: centre.lng },
      point,
      map.getZoom(),
      map.getContainer().clientHeight,
      map.getVerticalFieldOfView(),
    );
  }

  /**
   * Sizes the ring of degree marks to the Earth's disc, which stays in the middle of the stage,
   * and hides the ring when the Earth with its ring does not fit the stage.
   */
  private drawRing(): void {
    const { ring, map } = this;
    if (ring === null) return;
    const radius = earthDiscRadius(
      map.getZoom(),
      map.getCenter().lat,
      map.getContainer().clientHeight,
      map.getVerticalFieldOfView(),
    );
    ring.hidden = !ringFits(radius, stageSize(this.stage));
    const written = `${radius.toFixed(1)}px`;
    if (ring.hidden || written === this.ringRadius) return;
    this.ringRadius = written;
    ring.style.setProperty(RING_RADIUS_PROPERTY, written);
  }

  /**
   * The room a view that fills the stage leaves at its foot: the usual margin, or enough to keep
   * clear of the caption or key shown there.
   */
  private footRoom(): number {
    const { note, stage } = this;
    if (note === null || note.offsetHeight === 0) return FIT_PADDING_PX;
    return Math.max(FIT_PADDING_PX, stage.offsetHeight - note.offsetTop + NOTE_GAP_PX);
  }

  /** The note appeared, went or changed size: a view that fills the stage moves to fit it. */
  private keepClearOfNote(): void {
    if (this.view.kind === "area" && !this.movedByUser) this.applyView(FLIGHT_MS);
  }

  /**
   * On a phone the stage scrolls with the page (styles.css), so a swipe that starts on the globe
   * must not trap the page: there one finger and the wheel scroll the page, and two fingers, or
   * the wheel with Ctrl held, move the globe. A stage fixed beside the case file keeps every
   * gesture, and so does a globe on which a box is being drawn.
   */
  private syncGestures(): void {
    const scrollsWithPage = window.getComputedStyle(this.stage).position !== "fixed";
    const shares = scrollsWithPage && this.stopDrawing === null;
    const { cooperativeGestures } = this.map;
    if (shares === cooperativeGestures.isEnabled()) return;
    if (shares) cooperativeGestures.enable();
    else cooperativeGestures.disable();
  }

  /**
   * The padding that puts the globe's centre in the middle of the stage. The stage is either
   * fixed to the viewport or in the page's flow from its top, so its offsets are also its place
   * in the viewport before any scrolling.
   */
  private padding(): ReturnType<typeof stagePadding> {
    const { stage } = this;
    return stagePadding(
      { top: stage.offsetTop, left: stage.offsetLeft, width: stage.offsetWidth, height: stage.offsetHeight },
      { width: window.innerWidth, height: window.innerHeight },
    );
  }

  private setData(source: string, data: Parameters<GeoJSONSource["setData"]>[0]): void {
    if (this.removed) return;
    void this.map.getSource<GeoJSONSource>(source)?.setData(data);
  }

  private handleClick(event: MapMouseEvent): void {
    if (this.stopDrawing !== null) return;
    const cell = this.cells[this.cellIndexAt(event)];
    if (cell !== undefined) {
      this.cellHandler?.(cell);
      return;
    }
    if (this.pickHandler !== null && this.isOnEarth(event)) this.pick(event.lngLat);
  }

  private pick(point: LngLat): void {
    const wrapped = point.wrap();
    this.pickHandler?.({ lat: wrapped.lat, lon: wrapped.lng });
  }

  /** False for a pointer over the space around the Earth, whose coordinates lie on the horizon. */
  private isOnEarth(event: PointerEvent): boolean {
    return this.map.project(event.lngLat).dist(event.point) <= SURFACE_TOLERANCE_PX;
  }

  /** The place in `cells` of the region cell under the pointer, or `NO_CELL`. */
  private cellIndexAt(event: PointerEvent): number {
    if (this.cells.length === 0) return NO_CELL;
    const [feature] = this.map.queryRenderedFeatures(event.point, {
      layers: [LAYER.cellFill, LAYER.cellHatch],
    });
    const index: unknown = feature?.properties.index;
    return typeof index === "number" ? index : NO_CELL;
  }

  private handleHover(event: MapMouseEvent): void {
    if (this.stopDrawing !== null) return;
    const index = this.cellIndexAt(event);
    const cell = this.cells[index];
    if (cell === undefined || this.variable === null) {
      this.endHover();
      return;
    }
    this.map.getCanvas().style.cursor = "pointer";
    this.map.setFilter(LAYER.cellHover, ["==", ["get", "index"], index]);
    this.tooltip.setLngLat(event.lngLat).setDOMContent(tooltipContent(cell, this.variable)).addTo(this.map);
  }

  private endHover(): void {
    if (this.removed) return;
    this.map.getCanvas().style.cursor = "";
    this.map.setFilter(LAYER.cellHover, ["==", ["get", "index"], NO_CELL]);
    this.tooltip.remove();
  }

  /**
   * Lets a drag on the globe draw a box, shown snapped to whole degrees as it grows. Returns the
   * function that ends drawing and gives the globe back its dragging.
   */
  private startDrawing(onDrawn: (box: Box) => void): () => void {
    const { map } = this;
    // MapLibre owns the container's classes, so the drawing class is set here, not by React.
    const container = map.getContainer();
    container.classList.add(DRAWING_CLASS);
    this.takeOver();
    this.endHover();
    map.dragPan.disable();
    map.boxZoom.disable();
    map.doubleClickZoom.disable();
    let start: PointerEvent | null = null;

    const drawn = (from: PointerEvent, to: PointerEvent): Box =>
      boxFromDrag(wrapped(from.lngLat), wrapped(to.lngLat));
    const down = (event: PointerEvent): void => {
      start = event;
      this.setData(SOURCE.draftBox, collection([boxFeature(drawn(event, event))]));
    };
    const move = (event: PointerEvent): void => {
      if (start !== null) this.setData(SOURCE.draftBox, collection([boxFeature(drawn(start, event))]));
    };
    const up = (event: PointerEvent): void => {
      if (start === null) return;
      const from = start;
      start = null;
      this.setData(SOURCE.draftBox, collection([]));
      if (from.point.dist(event.point) >= MIN_DRAG_PX) onDrawn(drawn(from, event));
    };

    map.on("mousedown", down);
    map.on("touchstart", down);
    map.on("mousemove", move);
    map.on("touchmove", move);
    map.on("mouseup", up);
    map.on("touchend", up);
    return () => {
      map.off("mousedown", down);
      map.off("touchstart", down);
      map.off("mousemove", move);
      map.off("touchmove", move);
      map.off("mouseup", up);
      map.off("touchend", up);
      this.setData(SOURCE.draftBox, collection([]));
      map.dragPan.enable();
      map.boxZoom.enable();
      map.doubleClickZoom.enable();
      container.classList.remove(DRAWING_CLASS);
    };
  }
}

function stageSize(stage: HTMLElement): Size {
  return { width: stage.offsetWidth, height: stage.offsetHeight };
}

function wrapped(point: LngLat): LatLon {
  const inside = point.wrap();
  return { lat: inside.lat, lon: inside.lng };
}

/** A place's marker: its shape in its colour, with its name beside it. */
function markerElement(name: string, index: number): HTMLElement {
  const style = placeStyle(index);
  const marker = document.createElement("div");
  marker.className = "globe-marker";
  marker.style.setProperty("--place-color", style.color);
  const swatch = document.createElement("span");
  swatch.className = `shape-swatch shape-${style.shape}`;
  // Place names are user text, so they go in as text nodes and never as HTML.
  const label = document.createElement("span");
  label.className = "globe-label";
  label.textContent = name;
  marker.append(swatch, label);
  return marker;
}

/** What the pointer does with one pin of an example case. */
interface PinListeners {
  onOpen: () => void;
  onEnter: () => void;
  onLeave: () => void;
}

/**
 * The pin of an example case at one of its places: a push pin with a typed tag, "1 · Athens",
 * of which a small stage shows the number alone (styles.css, .example-pin-place).
 * One pin of the case also holds the card shown while the case is singled out, with the case's
 * question. The card is part of the pin, so a click on it opens the case too. The list of
 * examples is the way in for keyboards and screen readers, so the pins are hidden from them.
 */
function examplePinElement(
  pin: ExamplePin,
  place: MapPlace,
  hasCard: boolean,
  listeners: PinListeners,
): HTMLElement {
  const text = (className: string, content: string): HTMLElement => {
    const part = document.createElement("span");
    part.className = className;
    part.textContent = content;
    return part;
  };
  const element = document.createElement("div");
  element.className = hasCard ? "example-pin has-card" : "example-pin";
  element.setAttribute("aria-hidden", "true");
  const tag = text("example-pin-tag", String(pin.number));
  tag.append(text("example-pin-place", ` · ${place.name}`));
  element.append(tag);
  if (hasCard) {
    const card = document.createElement("span");
    card.className = "example-pin-card";
    card.append(
      text("example-pin-kicker", `Case ${pin.number} · ${place.name}`),
      text("example-pin-title", pin.title),
      text("example-pin-open", "Open this case →"),
    );
    element.append(card);
  }
  element.addEventListener("click", (event) => {
    // The click is for the pin, not for the point of the Earth under it.
    event.stopPropagation();
    listeners.onOpen();
  });
  element.addEventListener("mouseenter", listeners.onEnter);
  element.addEventListener("mouseleave", listeners.onLeave);
  return element;
}

/** The mark of a point the user picked: a ring, with no name until it becomes a place. */
function pickedPointElement(): HTMLElement {
  const mark = document.createElement("div");
  mark.className = "globe-picked";
  return mark;
}

/** The cell's numbers as text nodes, so nothing in them is read as HTML. */
function tooltipContent(cell: MapCell, variable: VariableSummary): HTMLElement {
  const tooltip = document.createElement("div");
  for (const line of cellTooltipLines(cell, variable)) {
    const row = document.createElement("div");
    row.textContent = line;
    tooltip.append(row);
  }
  return tooltip;
}

function hatchImage(): { width: number; height: number; data: Uint8Array } {
  const data = new Uint8Array(HATCH_SIZE_PX * HATCH_SIZE_PX * 4);
  for (let y = 0; y < HATCH_SIZE_PX; y += 1) {
    for (let x = 0; x < HATCH_SIZE_PX; x += 1) {
      const onLine = (x + y) % HATCH_SIZE_PX < HATCH_LINE_PX;
      data.set(onLine ? HATCH_LINE_RGBA : HATCH_GROUND_RGBA, (y * HATCH_SIZE_PX + x) * 4);
    }
  }
  return { width: HATCH_SIZE_PX, height: HATCH_SIZE_PX, data };
}

function seaImage(): { width: number; height: number; data: Uint8Array } {
  const data = new Uint8Array(SEA_TILE_WIDTH_PX * SEA_LINE_SPACING_PX * 4);
  for (let y = 0; y < SEA_LINE_SPACING_PX; y += 1) {
    for (let x = 0; x < SEA_TILE_WIDTH_PX; x += 1) {
      data.set(y === 0 ? SEA_LINE_RGBA : SEA_GROUND_RGBA, (y * SEA_TILE_WIDTH_PX + x) * 4);
    }
  }
  return { width: SEA_TILE_WIDTH_PX, height: SEA_LINE_SPACING_PX, data };
}

interface GlobeCanvasProps {
  /** The part of the screen the globe is seen through; the Earth is centred in it. */
  stageRef: RefObject<HTMLElement | null>;
  /** Called with the globe once it can take data, and with null when it goes away. */
  onReady: (handle: GlobeHandle | null) => void;
  /** Called when the browser cannot draw the globe. */
  onUnavailable: () => void;
}

/**
 * The globe itself: the Earth on a WebGL canvas that fills its container. This module carries
 * MapLibre, so callers load it with React.lazy.
 */
export default function GlobeCanvas({ stageRef, onReady, onUnavailable }: GlobeCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const ready = useEffectEvent(onReady);
  const unavailable = useEffectEvent(onUnavailable);

  useEffect(() => {
    const container = containerRef.current;
    const stage = stageRef.current;
    if (container === null || stage === null) return;
    let globe: Globe;
    try {
      globe = new Globe(container, stage);
    } catch (error) {
      if (!(error instanceof GPUInitializationError)) throw error;
      unavailable();
      return;
    }
    let mounted = true;
    globe.whenLoaded(() => {
      if (mounted) ready(globe);
    });
    return () => {
      mounted = false;
      ready(null);
      globe.remove();
    };
  }, [stageRef]);

  return <div className="globe-canvas" ref={containerRef} />;
}
