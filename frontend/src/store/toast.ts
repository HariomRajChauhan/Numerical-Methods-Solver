import { create } from "zustand";

export type ToastTone = "success" | "error" | "info";

export interface ToastMessage {
  id: number;
  tone: ToastTone;
  title: string;
  message?: string;
  /** Auto-dismiss delay in milliseconds. */
  duration: number;
}

interface ToastState {
  toasts: ToastMessage[];
  push: (toast: Omit<ToastMessage, "id" | "duration"> & { duration?: number }) => number;
  dismiss: (id: number) => void;
  clear: () => void;
}

let nextId = 1;

export const useToastStore = create<ToastState>()((set) => ({
  toasts: [],
  push: (input) => {
    const id = nextId++;
    set((state) => ({
      toasts: [
        ...state.toasts,
        { ...input, id, duration: input.duration ?? 4200 },
      ].slice(-4),
    }));
    return id;
  },
  dismiss: (id) =>
    set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
  clear: () => set({ toasts: [] }),
}));

/** Fire a toast from anywhere in the app without subscribing to the store. */
export function toast(input: {
  tone: ToastTone;
  title: string;
  message?: string;
  duration?: number;
}): number {
  return useToastStore.getState().push(input);
}
