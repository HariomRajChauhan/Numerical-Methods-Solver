import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { Sidebar } from "../components/layout/Sidebar";
import { useSidebarStore } from "../store/sidebar";
import { useCatalogStore } from "../store/catalog";

import type { ChapterId, MethodMeta } from "../types/api";

const mockChapters = [
  {
    id: "ch1_nonlinear" as const,
    number: 1,
    title: "Non-linear Equations",
    description: "Root-finding methods",
    method_count: 5,
    available_count: 5,
  },
  {
    id: "ch2_linear" as const,
    number: 2,
    title: "Linear Equations",
    description: "System solvers",
    method_count: 4,
    available_count: 4,
  },
];

const mockMethods: MethodMeta[] = [
  {
    id: "bisection",
    chapter: "ch1_nonlinear" as ChapterId,
    variables: ["x"],
    name: "Bisection Method",
    status: "available" as const,
    summary: "Root finding by bisection",
    theory: "",
    pseudocode: "",
    formulas: [],
    input_schema: [],
    examples: [],
    chapter_title: "Non-linear Equations",
    chapter_number: 1,
  },
  {
    id: "newton_raphson",
    chapter: "ch1_nonlinear" as ChapterId,
    variables: ["x"],
    name: "Newton-Raphson Method",
    status: "available" as const,
    summary: "Root finding by Newton-Raphson",
    theory: "",
    pseudocode: "",
    formulas: [],
    input_schema: [],
    examples: [],
    chapter_title: "Non-linear Equations",
    chapter_number: 1,
  },
];

function resetStore() {
  useSidebarStore.setState({
    mode: "expanded",
    width: 280,
    autoCollapse: false,
    pinned: true,
    recent: [],
    favorites: [],
    focusMode: false,
  });
  useCatalogStore.setState({
    chapters: mockChapters,
    methods: mockMethods,
    status: "ready",
    error: undefined,
  });
}

beforeEach(() => {
  resetStore();
  if (typeof localStorage !== "undefined") localStorage.clear();
});

afterEach(() => {
  resetStore();
  if (typeof localStorage !== "undefined") localStorage.clear();
});

describe("Sidebar store", () => {
  beforeEach(() => {
    resetStore();
  });

  it("cycles through modes in order", () => {
    const { cycle } = useSidebarStore.getState();
    expect(useSidebarStore.getState().mode).toBe("expanded");
    cycle();
    expect(useSidebarStore.getState().mode).toBe("hidden");
    cycle();
    expect(useSidebarStore.getState().mode).toBe("expanded");
  });

  it("clamps width between 240 and 420", () => {
    const { setWidth } = useSidebarStore.getState();
    expect(useSidebarStore.getState().width).toBe(280);
    setWidth(100);
    expect(useSidebarStore.getState().width).toBe(240);
    setWidth(500);
    expect(useSidebarStore.getState().width).toBe(420);
    setWidth(300);
    expect(useSidebarStore.getState().width).toBe(300);
  });

  it("tracks recent methods up to 5", () => {
    const { addRecent } = useSidebarStore.getState();
    expect(useSidebarStore.getState().recent).toEqual([]);
    addRecent("method1");
    expect(useSidebarStore.getState().recent).toEqual(["method1"]);
    addRecent("method2");
    expect(useSidebarStore.getState().recent).toEqual(["method2", "method1"]);
    addRecent("method1");
    expect(useSidebarStore.getState().recent).toEqual(["method1", "method2"]);
    addRecent("method3");
    addRecent("method4");
    addRecent("method5");
    addRecent("method6");
    expect(useSidebarStore.getState().recent.length).toBeLessThanOrEqual(5);
  });

  it("toggles favorites", () => {
    const { toggleFavorite, isFavorite, favorites } = useSidebarStore.getState();
    expect(favorites).toEqual([]);
    toggleFavorite("method1");
    expect(isFavorite("method1")).toBe(true);
    toggleFavorite("method1");
    expect(isFavorite("method1")).toBe(false);
  });

  it("persists mode to localStorage", () => {
    act(() => {
      useSidebarStore.getState().setMode("expanded");
    });
    if (typeof localStorage !== "undefined") {
      expect(localStorage.getItem("nms-sidebar")).toContain('"mode":"expanded"');
    }
  });
});

describe("Sidebar rendering (expanded state)", () => {
  it("renders chapter titles and methods in expanded state", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Non-linear Equations")).toBeInTheDocument();
    expect(screen.getByText("Linear Equations")).toBeInTheDocument();
    expect(screen.getByText("Bisection Method")).toBeInTheDocument();
  });
});
