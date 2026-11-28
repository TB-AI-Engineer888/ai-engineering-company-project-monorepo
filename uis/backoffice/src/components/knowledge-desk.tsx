"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";

const EXAMPLES = [
  "Is there a charge for cancelling 12 hours in advance?",
  "What do I need to bring to my first appointment?",
  "Which insurers do we accept?",
];

export function KnowledgeDesk() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const saved = window.localStorage.getItem("healthcore-theme");
    const next = saved === "dark" ? "dark" : "light";
    document.documentElement.classList.toggle("dark", next === "dark");
    setTheme(next);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    window.localStorage.setItem("healthcore-theme", next);
    setTheme(next);
  }

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setAnswer(null);
      setError("Type a question first.");
      return;
    }
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const response = await fetch("/knowledge/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      const payload = (await response.json()) as { answer?: string; detail?: string };
      if (!response.ok || !payload.answer) {
        setError(payload.detail || `The desk assistant could not answer (${response.status}).`);
        return;
      }
      setAnswer(payload.answer);
    } catch {
      setError("The desk assistant could not be reached. The answer box stays empty until a reply arrives.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Coordinator desk</h2>
          <p className="mt-2 text-muted-foreground">
            Ask a front-desk question. The reply comes from HealthCore policy documents, in the voice of Priya Nair&apos;s coordinators.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={toggleTheme}>
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Question</CardTitle>
          <CardDescription>Coverage, cancellations, referrals, and new-patient steps.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={(event) => void ask(event)}>
            <div className="grid gap-1.5">
              <Label htmlFor="desk-question">What should the coordinator say?</Label>
              <textarea
                id="desk-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              />
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              {EXAMPLES.map((example) => (
                <Button
                  key={example}
                  type="button"
                  variant="outline"
                  onClick={() => setQuestion(example)}
                >
                  {example}
                </Button>
              ))}
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Checking the policy documents..." : "Ask the desk"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>The assistant did not answer</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Answer</CardTitle>
          <CardDescription>
            {loading
              ? "Looking through the indexed policies."
              : answer
                ? "Generated from the retrieved policy excerpts."
                : "No answer yet."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Checking the policy documents...</p>
          ) : answer ? (
            <p className="whitespace-pre-wrap text-sm leading-6">{answer}</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              The answer appears here after a successful reply. A failed request stays in the alert above and does not look like an answer.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
