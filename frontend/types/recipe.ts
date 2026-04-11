export interface RecipeIngredient {
  name: string;
  quantity: number | null;
  unit: string | null;
}

export interface RecipeStep {
  step_number: number;
  instruction: string;
}

export interface Recipe {
  id: string;
  title: string;
  source_url: string;
  ingredients: RecipeIngredient[];
  steps: RecipeStep[];
  cuisine: string | null;
  tags: string[] | null;
  scraped_at: string;
}

export interface RecommendationItem {
  recipe_id: string;
  title: string;
  match_score: number;
  matched_ingredients: string[];
  missing_ingredients: string[];
  cuisine: string | null;
  source_url: string;
}

export interface RecommendResponse {
  recommendations: RecommendationItem[];
}
