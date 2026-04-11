import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import type { ScanResponse } from "@/types/fridge";

const mockScanResponse: ScanResponse = {
  detected: [
    { item_name: "eggs", category: "protein", quantity: 6, unit: "count", confidence: 0.95 },
  ],
  saved_count: 1,
};

const server = setupServer(
  http.post("http://localhost:8000/api/fridge/scan", () => HttpResponse.json(mockScanResponse))
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(createElement(QueryClientProvider, { client: queryClient }, ui));
}

describe("Scan page", () => {
  it("renders file input for camera", async () => {
    const { default: ScanPage } = await import("@/app/fridge/scan/page");
    renderWithQueryClient(createElement(ScanPage));
    expect(screen.getByText("Choose Photo")).toBeInTheDocument();
  });

  it("shows detected items after scan", async () => {
    const { default: ScanPage } = await import("@/app/fridge/scan/page");
    renderWithQueryClient(createElement(ScanPage));

    const file = new File(["fake-image"], "fridge.jpg", { type: "image/jpeg" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    // Trigger file selection
    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText("eggs")).toBeInTheDocument();
    });
  });
});
