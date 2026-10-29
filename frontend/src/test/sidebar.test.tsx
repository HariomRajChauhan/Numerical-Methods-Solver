import { act, fireEvent, render, screen } from "@testing-library/react";
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
    mode: "rail",
    width: 280,
    autoCollapse: false,
    pinned: false,
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
  localStorage.clear();
});

afterEach(() => {
  resetStore();
  localStorage.clear();
});

describe("Sidebar store", () => {
  beforeEach(() => {
    resetStore();
  });

  it("cycles through modes in order", () => {
    const { cycle } = useSidebarStore.getState();
    expect(useSidebarStore.getState().mode).toBe("rail");
    cycle();
    expect(useSidebarStore.getState().mode).toBe("hidden");
    cycle();
    expect(useSidebarStore.getState().mode).toBe("expanded");
    cycle();
    expect(useSidebarStore.getState().mode).toBe("rail");
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

  it("toggles auto-collapse", () => {
    const { setAutoCollapse } = useSidebarStore.getState();
    setAutoCollapse(true);
    expect(useSidebarStore.getState().autoCollapse).toBe(true);
  });

  it("toggles pin", () => {
    const { setPinned } = useSidebarStore.getState();
    setPinned(true);
    expect(useSidebarStore.getState().pinned).toBe(true);
  });

  it("persists mode to localStorage", () => {
    act(() => {
      useSidebarStore.getState().setMode("expanded");
    });
    expect(localStorage.getItem("nms-sidebar")).toContain('"mode":"expanded"');
  });
});

describe("Sidebar rendering (rail state - default)", () => {
  it("renders chapter icons in rail state", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByRole("button", { name: "Non-linear Equations" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Linear Equations" })).toBeInTheDocument();
    // Methods should NOT be visible in rail state
    expect(screen.queryByText("Bisection Method")).not.toBeInTheDocument();
  });

  it("opens flyout on chapter icon click", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );
    const chapterIcon = screen.getByRole("button", { name: "Non-linear Equations" });
    act(() => {
      fireEvent.click(chapterIcon);
    });
    expect(screen.getByText("Bisection Method")).toBeInTheDocument();
    expect(screen.getByText("Newton-Raphson Method")).toBeInTheDocument();
  });

  it("closes flyout on method selection", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );
    const chapterIcon = screen.getByRole("button", { name: "Non-linear Equations" });
    act(() => {
      fireEvent.click(chapterIcon);
    });
    const methodLink = screen.getByText("Bisection Method");
    act(() => {
      fireEvent.click(methodLink);
    });
    expect(screen.queryByText("Bisection Method")).not.toBeInTheDocument();
  });

  it("closes flyout on Escape", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );
    const chapterIcon = screen.getByRole("button", { name: "Non-linear Equations" });
    act(() => {
      fireEvent.click(chapterIcon);
    });
    expect(screen.getByText("Bisection Method")).toBeInTheDocument();
    act(() => {
      fireEvent.keyDown(document, { key: "Escape" });
    });
    expect(screen.queryByText("Bisection Method")).not.toBeInTheDocument();
  });
});
