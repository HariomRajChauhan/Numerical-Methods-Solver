import "@testing-library/jest-dom/vitest";

// Mock ResizeObserver for jsdom
class MockResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

window.ResizeObserver = MockResizeObserver;
global.ResizeObserver = MockResizeObserver;
