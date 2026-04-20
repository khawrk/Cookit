"use client";

import Link from "next/link";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useRecipe, useRecipeTranslation } from "@/lib/hooks/useRecipes";
import { useLocaleStore } from "@/lib/stores/localeStore";
import type { RecipeIngredient, RecipeStep } from "@/types/recipe";

/** Returns the display measure for an ingredient regardless of which shape it arrived in. */
function ingredientMeasure(ing: RecipeIngredient): string {
  if (ing.measure) return ing.measure;
  const parts: string[] = [];
  if (ing.quantity != null) parts.push(String(ing.quantity));
  if (ing.unit) parts.push(ing.unit);
  return parts.join(" ");
}

/** Filters out bare "STEP N" header entries that MealDB injects between real instructions. */
function filterSteps(steps: RecipeStep[]): RecipeStep[] {
  return steps.filter((s) => {
    const text = s.instruction.trim();
    return !/^step\s+\d+$/i.test(text) && !/^\d+$/.test(text);
  });
}

export default function RecipeDetailPage({ params }: { params: { id: string } }) {
  const { t } = useTranslation();
  const { locale } = useLocaleStore();
  const { id } = params;
  const { data: recipe, isLoading, error } = useRecipe(id);
  const isThai = locale === "th";
  const { data: translation, isLoading: translationLoading } = useRecipeTranslation(id, isThai);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !recipe) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-500 mb-4">{t("recipeDetail.notFound")}</p>
          <Link href="/recipes" className="text-green-600 hover:underline text-sm">
            {t("recipeDetail.backToRecipes")}
          </Link>
        </div>
      </div>
    );
  }

  const displayTitle = (isThai && translation?.title) ? translation.title : recipe.title;
  const ingredients = ((isThai && translation?.ingredients) ? translation.ingredients : recipe.ingredients) as RecipeIngredient[];
  const steps = filterSteps(((isThai && translation?.steps) ? translation.steps : recipe.steps) as RecipeStep[]);

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 py-8">

        <Link
          href="/recipes"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 mb-6"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {t("recipeDetail.backLink")}
        </Link>

        {/* Title + meta */}
        {isThai && translationLoading && (
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
            <Spinner size="sm" />
            <span>Translating…</span>
          </div>
        )}
        <h1 className="text-2xl font-bold text-slate-900 leading-tight mb-3">{displayTitle}</h1>
        <div className="flex flex-wrap items-center gap-2 mb-8">
          {recipe.cuisine && <Badge variant="blue">{recipe.cuisine}</Badge>}
          {recipe.tags?.filter(Boolean).map((tag) => (
            <Badge key={tag} variant="gray">{tag}</Badge>
          ))}
        </div>

        {/* Ingredients */}
        <Card className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <h2 className="text-base font-semibold text-slate-900">
              {t("recipeDetail.ingredientsTitle")}
              <span className="ml-2 text-sm font-normal text-slate-400">({ingredients.length})</span>
            </h2>
          </div>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6">
            {ingredients.map((ing, idx) => {
              const measure = ingredientMeasure(ing);
              return (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                  <span className="text-slate-700">
                    {measure && (
                      <span className="font-medium text-slate-900">{measure} </span>
                    )}
                    {ing.name}
                  </span>
                </li>
              );
            })}
          </ul>
        </Card>

        {/* Instructions */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <h2 className="text-base font-semibold text-slate-900">
              {t("recipeDetail.instructionsTitle")}
              <span className="ml-2 text-sm font-normal text-slate-400">({t("recipeDetail.steps", { n: steps.length })})</span>
            </h2>
          </div>
          <ol className="flex flex-col gap-5">
            {steps.map((step, idx) => (
              <li key={step.step_number} className="flex gap-4">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {idx + 1}
                </span>
                <p className="text-slate-700 text-sm leading-relaxed">{step.instruction}</p>
              </li>
            ))}
          </ol>
        </Card>

        {/* Source */}
        {recipe.source_url && (
          <p className="mt-6 text-xs text-slate-400 text-center">
            {t("recipeDetail.recipeFrom")}{" "}
            <a
              href={recipe.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-slate-600"
            >
              {(() => {
                try {
                  return new URL(recipe.source_url).hostname.replace(/^www\./, "");
                } catch {
                  return recipe.source_url;
                }
              })()}
            </a>
          </p>
        )}

      </div>
    </div>
  );
}
