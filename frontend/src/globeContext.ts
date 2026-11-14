/**
 * How the views reach the globe (spec 3, "The globe"). The app keeps one globe behind every
 * view; a view tells it what to show through the hooks here. This module does not load
 * MapLibre, so the first paint never waits for the globe.
 */

import { createContext, useContext, useEffect, useEffectEvent } from "react";
import type { Box, MapCell, TrendMap } from "./api";
import type { ExampleLink, ExampleListeners, ExamplePin } from "./examplePins";
import type { MapPlace } from "./mapCell";
import type { LatLon } from "./regionBox";

/** What the globe can be told to do. Every method is safe to call in any order. */
export interface GlobeHandle {
  /**
   * Marks the places and outlines their grid cells, then turns the Earth to face them. With no
   * place, the whole Earth is shown, turning slowly until the user touches it.
   */
  showPlaces(places: readonly MapPlace[]): void;
  /** Removes the places without moving the view. */
  clearPlaces(): void;
  /** Marks the point the user picked, until it becomes a place or is dismissed; null removes the mark. */
  showPickedPoint(point: LatLon | null): void;
  /** Closes in on the places until their grid cells can be seen. */
  zoomToCells(): void;
  /** Sets who hears of a point the user picks; null turns picking off. */
  setPickHandler(handler: ((point: LatLon) => void) | null): void;
  /**
   * Draws a region map: the dashed outline of `box`, and each cell of `trendMap` coloured on a
   * scale from -scaleLimit to +scaleLimit. A box that differs from the one shown moves the view to it.
   */
  showRegion(box: Box | null, trendMap: TrendMap | null, scaleLimit: number): void;
  /** Removes the region map without moving the view. */
  clearRegion(): void;
  /** Sets who hears of a cell the user opens; null turns it off. */
  setCellHandler(handler: ((cell: MapCell) => void) | null): void;
  /** While a handler is set, dragging draws a box instead of turning the Earth. */
  setDrawHandler(handler: ((box: Box) => void) | null): void;
  /**
   * Pins the example cases to the globe: a pin with the case's number at each place a case
   * tests, and a line between the places of one case. The listeners hear of a pin the user
   * points at or opens. An empty list takes the pins away.
   */
  showExamples(pins: readonly ExamplePin[], listeners: ExampleListeners): void;
  /**
   * Singles out one example: one of its pins shows the case's question, the Earth turns to face
   * its places if the link asks for that, and the link hears where its pins are (see
   * ExampleLink). The idle turn waits meanwhile. Null singles out none and leaves the view as it
   * is; an idle turn that was held up goes on a few seconds later.
   */
  linkExample(link: ExampleLink | null): void;
  /** Zooms by `levels`: positive in, negative out. */
  zoomBy(levels: number): void;
  /** Pulls back until the whole Earth is in view, facing what is shown. */
  showEarth(): void;
}

/** "loading" until the globe has drawn; "unavailable" when the browser cannot draw it. */
export type GlobeStatus = "loading" | "ready" | "unavailable";

export interface GlobeState {
  /** The globe, once it is ready. */
  handle: GlobeHandle | null;
  status: GlobeStatus;
}

export const GLOBE_LOADING: GlobeState = { handle: null, status: "loading" };
export const GLOBE_UNAVAILABLE: GlobeState = { handle: null, status: "unavailable" };

export const GlobeContext = createContext<GlobeState>(GLOBE_LOADING);

/** The globe's state, for a control that acts on it. */
export function useGlobe(): GlobeState {
  return useContext(GlobeContext);
}

/**
 * The element on the stage where a view draws its note: a caption for what the globe shows, or
 * the key to a region map. Null until the stage is in the page, and where there is no globe.
 */
export const StageNoteContext = createContext<HTMLElement | null>(null);

/**
 * Shows the places and the picked point on the globe while the calling view is on screen, and
 * reports the point the user picks there. `places` and `pickedPoint` should keep their identity
 * between renders unless they change.
 */
export function useGlobePlaces(
  places: readonly MapPlace[],
  pickedPoint: LatLon | null,
  onPick: (point: LatLon) => void,
): void {
  const { handle } = useContext(GlobeContext);
  const pick = useEffectEvent(onPick);

  useEffect(() => {
    if (handle === null) return;
    handle.setPickHandler((point) => pick(point));
    return () => {
      handle.setPickHandler(null);
      handle.showPickedPoint(null);
      handle.clearPlaces();
    };
  }, [handle]);

  useEffect(() => {
    handle?.showPlaces(places);
  }, [handle, places]);

  useEffect(() => {
    handle?.showPickedPoint(pickedPoint);
  }, [handle, pickedPoint]);
}

/**
 * Pins the example cases to the globe while the calling view is on screen, and reports the case
 * whose pin the user points at or opens. `pins` should keep its identity between renders unless
 * it changes.
 */
export function useGlobeExamples(pins: readonly ExamplePin[], listeners: ExampleListeners): void {
  const { handle } = useContext(GlobeContext);
  const open = useEffectEvent(listeners.onOpen);
  const point = useEffectEvent(listeners.onPoint);

  useEffect(() => {
    if (handle === null || pins.length === 0) return;
    const heard: ExampleListeners = { onOpen: (pin) => open(pin), onPoint: (pin) => point(pin) };
    handle.showExamples(pins, heard);
    return () => handle.showExamples([], heard);
  }, [handle, pins]);
}

/** A region map to draw on the globe, and what the user can do on it. */
export interface GlobeRegion {
  /** The box asked for, drawn as a dashed outline; null before a map is set up. */
  box: Box | null;
  /** The cells to draw; null while there is no map. */
  trendMap: TrendMap | null;
  /** The colour scale runs from -scaleLimit to +scaleLimit. */
  scaleLimit: number;
  /** While true, dragging on the globe draws a box instead of turning the Earth. */
  drawing: boolean;
  onBoxDrawn: (box: Box) => void;
  onOpenCell: (cell: MapCell) => void;
}

/**
 * Draws the region map on the globe while the calling view is on screen. `box` and `trendMap`
 * should keep their identity between renders unless they change.
 */
export function useGlobeRegion(region: GlobeRegion): void {
  const { handle } = useContext(GlobeContext);
  const { box, trendMap, scaleLimit, drawing } = region;
  const openCell = useEffectEvent(region.onOpenCell);
  const finishDrawing = useEffectEvent(region.onBoxDrawn);

  useEffect(() => {
    if (handle === null) return;
    handle.setCellHandler((cell) => openCell(cell));
    return () => {
      handle.setCellHandler(null);
      handle.clearRegion();
    };
  }, [handle]);

  useEffect(() => {
    handle?.showRegion(box, trendMap, scaleLimit);
  }, [handle, box, trendMap, scaleLimit]);

  useEffect(() => {
    if (handle === null || !drawing) return;
    handle.setDrawHandler((drawn) => finishDrawing(drawn));
    return () => handle.setDrawHandler(null);
  }, [handle, drawing]);
}
