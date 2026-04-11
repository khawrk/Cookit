"use client";

import { use } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useRecipe } from "@/lib/hooks/useRecipes";
import type { RecipeIngredient, RecipeStep } from "@/types/recipe";

export default function RecipeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: recipe, isLoading, error } = useRecipe(id);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !recipe) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">Recipe not found.</p>
          <Link href="/recipes" className="text-green-600 hover:underline">
            ← Back to recipes
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Link href="/recipes" className="text-sm text-green-600 hover:underline mb-4 inline-block">
          ← Back to recommendations
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">{recipe.title}</h1>
        <div className="flex items-center gap-2 mb-6">
          {recipe.cuisine && <Badge variant="blue">{recipe.cuisine}</Badge>}
          {recipe.tags?.map((tag) => (
            <Badge key={tag} variant="gray">
              {tag}
            </Badge>
          ))}
        </div>

        <Card className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Ingredients</h2>
          <ul className="flex flex-col gap-2">
            {(recipe.ingredients as RecipeIngredient[]).map((ing, idx) => (
              <li key={idx} className="flex items-baseline gap-2 text-sm">
                <span className="w-2 h-2 rounded-full bg-green-500 shrink-0 mt-1.5" />
                <span className="text-gray-800">
                  {ing.quantity != null && `${ing.quantity} `}
                  {ing.unit && `${ing.unit} `}
                  <span className="font-medium">{ing.name}</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Instructions</h2>
          <ol className="flex flex-col gap-4">
            {(recipe.steps as RecipeStep[]).map((step) => (
              <li key={step.step_number} className="flex gap-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-green-600 text-white text-sm font-semibold flex items-center justify-center">
                  {step.step_number}
                </span>
                <p className="text-gray-700 text-sm leading-relaxed pt-0.5">{step.instruction}</p>
              </li>
            ))}
          </ol>
        </Card>

        <p className="mt-6 text-xs text-gray-400 text-center">
          Source:{" "}
          <a href={recipe.source_url} target="_blank" rel="noopener noreferrer" className="underline">
            {recipe.source_url}
          </a>
        </p>
      </div>
    </div>
  );
}
