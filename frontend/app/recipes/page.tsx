"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useRecommendations } from "@/lib/hooks/useRecipes";

function MatchBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-400" : "bg-slate-300";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function RecipesPage() {
  const { data, isLoading, error } = useRecommendations();

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 py-6">

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Recipes for You</h1>
          <p className="text-slate-500 text-sm mt-1">Based on what's in your fridge right now</p>
        </div>

        {isLoading && (
          <div className="flex flex-col items-center gap-3 py-16">
            <Spinner size="lg" />
            <p className="text-slate-500 text-sm">Finding the best recipes for your fridge…</p>
          </div>
        )}

        {error && (
          <Card className="text-center py-8 border-red-100">
            <p className="text-red-500 text-sm">Failed to load recommendations.</p>
            <Link href="/fridge" className="text-sm text-green-600 hover:underline mt-2 inline-block">
              ← Back to Fridge
            </Link>
          </Card>
        )}

        {data && data.recommendations.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <svg className="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-slate-600 font-medium mb-1">No recipes found</p>
            <p className="text-slate-400 text-sm mb-4">Try adding more items to your fridge</p>
            <Link href="/fridge/scan" className="text-green-600 hover:underline text-sm font-medium">
              Scan your fridge →
            </Link>
          </div>
        )}

        {data && data.recommendations.length > 0 && (
          <div className="flex flex-col gap-3">
            {data.recommendations.map((rec) => (
              <Link key={rec.recipe_id} href={`/recipes/${rec.recipe_id}`}>
                <Card className="hover:shadow-md hover:border-slate-300 transition-all cursor-pointer active:scale-[0.99]">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <h2 className="font-semibold text-slate-900 leading-snug">{rec.title}</h2>
                      {rec.cuisine && (
                        <Badge variant="blue" className="mt-1">{rec.cuisine}</Badge>
                      )}
                    </div>
                    <svg className="h-4 w-4 text-slate-300 shrink-0 mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                  <MatchBar score={rec.match_score} />
                  <div className="mt-3 flex flex-col gap-1">
                    {rec.matched_ingredients.length > 0 && (
                      <p className="text-xs text-slate-500">
                        <span className="text-green-600 font-medium">Have: </span>
                        {rec.matched_ingredients.slice(0, 5).join(", ")}
                        {rec.matched_ingredients.length > 5 && (
                          <span className="text-slate-400"> +{rec.matched_ingredients.length - 5} more</span>
                        )}
                      </p>
                    )}
                    {rec.missing_ingredients.length > 0 && (
                      <p className="text-xs text-slate-500">
                        <span className="text-orange-500 font-medium">Need: </span>
                        {rec.missing_ingredients.slice(0, 4).join(", ")}
                        {rec.missing_ingredients.length > 4 && (
                          <span className="text-slate-400"> +{rec.missing_ingredients.length - 4} more</span>
                        )}
                      </p>
                    )}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
