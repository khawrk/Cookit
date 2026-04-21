import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CondimentCatalogItem,
  CorrectionEntry,
  CorrectionsResponse,
  FridgeItem,
  FridgeItemIn,
  FridgeItemUpdate,
  ScanResponse,
} from "@/types/fridge";

export function useFridgeItems() {
  return useQuery({
    queryKey: ["fridge", "items"],
    queryFn: () => api.get<FridgeItem[]>("/api/fridge/items"),
  });
}

export function useScanFridge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.postForm<ScanResponse>("/api/fridge/scan", formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fridge", "items"] });
    },
  });
}

export function useAddFridgeItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FridgeItemIn) => api.post<FridgeItem>("/api/fridge/items", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fridge", "items"] });
    },
  });
}

export function useUpdateFridgeItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: FridgeItemUpdate }) =>
      api.patch<FridgeItem>(`/api/fridge/items/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fridge", "items"] });
    },
  });
}

export function useDeleteFridgeItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/api/fridge/items/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fridge", "items"] });
    },
  });
}

export function useCondimentsCatalog() {
  return useQuery({
    queryKey: ["fridge", "catalog"],
    queryFn: () => api.get<CondimentCatalogItem[]>("/api/fridge/catalog"),
    staleTime: 1000 * 60 * 60, // 1 hour — catalog rarely changes
  });
}

export function useSubmitCorrections() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (corrections: CorrectionEntry[]) =>
      api.post<CorrectionsResponse>("/api/fridge/corrections", { corrections }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fridge", "items"] });
    },
  });
}
