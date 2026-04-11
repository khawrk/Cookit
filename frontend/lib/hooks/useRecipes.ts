import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RecommendResponse, Recipe } from "@/types/recipe";

export function useRecommendations() {
  return useQuery({
    queryKey: ["recipes", "recommendations"],
    queryFn: () => api.get<RecommendResponse>("/api/recipes/recommend"),
  });
}

export function useRecipe(id: string) {
  return useQuery({
    queryKey: ["recipes", id],
    queryFn: () => api.get<Recipe>(`/api/recipes/${id}`),
    enabled: Boolean(id),
  });
}

export function useRecipeSearch(query: string) {
  return useQuery({
    queryKey: ["recipes", "search", query],
    queryFn: () => api.get<Recipe[]>(`/api/recipes/search?q=${encodeURIComponent(query)}`),
    enabled: query.length > 0,
  });
}
