import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RecommendResponse, Recipe, TranslatedRecipe } from "@/types/recipe";

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

export function useRecipeTranslation(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["recipes", id, "translation", "th"],
    queryFn: () => api.get<TranslatedRecipe>(`/api/recipes/${id}/translate?lang=th`),
    enabled: enabled && Boolean(id),
    staleTime: Infinity, // translations don't change within a session
  });
}

export function useRecipeSearch(query: string) {
  return useQuery({
    queryKey: ["recipes", "search", query],
    queryFn: () => api.get<Recipe[]>(`/api/recipes/search?q=${encodeURIComponent(query)}`),
    enabled: query.length > 0,
  });
}
