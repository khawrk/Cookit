import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import type { CondimentCatalogItem } from "@/types/fridge";

const mockCatalog: CondimentCatalogItem[] = [
  { id: "c1", name: "soy sauce", category: "condiment", default_unit: "tbsp" },
  { id: "c2", name: "fish sauce", category: "condiment", default_unit: "tbsp" },
  { id: "c3", name: "oyster sauce", category: "condiment", default_unit: "tbsp" },
];

const server = setupServer(
  http.get("http://localhost:8000/api/fridge/catalog", () => HttpResponse.json(mockCatalog)),
  http.post("http://localhost:8000/api/fridge/items", () =>
    HttpResponse.json({ id: "new-id", item_name: "soy sauce", source: "manual", updated_at: new Date().toISOString() })
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(createElement(QueryClientProvider, { client: queryClient }, ui));
}

describe("Manual Add Page — catalog", () => {
  it("shows condiments from catalog", async () => {
    const { default: ManualAddPage } = await import("@/app/fridge/manual/page");
    renderWithQueryClient(createElement(ManualAddPage));

    await waitFor(() => {
      expect(screen.getByText("soy sauce")).toBeInTheDocument();
      expect(screen.getByText("fish sauce")).toBeInTheDocument();
    });
  });

  it("filters catalog on search input", async () => {
    const { default: ManualAddPage } = await import("@/app/fridge/manual/page");
    renderWithQueryClient(createElement(ManualAddPage));

    await waitFor(() => expect(screen.getByText("soy sauce")).toBeInTheDocument());

    const searchInput = screen.getByPlaceholderText("Search condiments…");
    await userEvent.type(searchInput, "fish");

    expect(screen.queryByText("soy sauce")).not.toBeInTheDocument();
    expect(screen.getByText("fish sauce")).toBeInTheDocument();
  });
});
