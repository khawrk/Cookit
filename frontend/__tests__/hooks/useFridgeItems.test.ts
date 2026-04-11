import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import { useFridgeItems } from "@/lib/hooks/useFridge";
import type { FridgeItem } from "@/types/fridge";

const mockItems: FridgeItem[] = [
  {
    id: "uuid-1",
    item_name: "chicken breast",
    category: "protein",
    quantity: 2,
    unit: "count",
    source: "vision",
    confidence: 0.95,
    updated_at: new Date().toISOString(),
  },
];

const server = setupServer(
  http.get("http://localhost:8000/api/fridge/items", () => HttpResponse.json(mockItems))
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useFridgeItems", () => {
  it("returns fridge items from API", async () => {
    const { result } = renderHook(() => useFridgeItems(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].item_name).toBe("chicken breast");
  });

  it("handles API error", async () => {
    server.use(
      http.get("http://localhost:8000/api/fridge/items", () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 })
      )
    );
    const { result } = renderHook(() => useFridgeItems(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
