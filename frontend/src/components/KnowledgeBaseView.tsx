import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Database,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";

import { apiClient, ApiError } from "../api/client";
import type {
  KBArticle,
  KBSearchHit,
  TicketCategory,
} from "../types/api";
import { CATEGORY_OPTIONS, formatCategory, formatPercent } from "../utils/format";

export function KnowledgeBaseView() {
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<TicketCategory | "">("");

  const [searchQuery, setSearchQuery] = useState("двойное списание по карте возврат");
  const [searchCategory, setSearchCategory] = useState<TicketCategory | "">("");
  const [topK, setTopK] = useState(3);
  const [minScore, setMinScore] = useState(0.15);
  const [searching, setSearching] = useState(false);
  const [searchHits, setSearchHits] = useState<KBSearchHit[] | null>(null);

  const [showEditor, setShowEditor] = useState(false);
  const [newSlug, setNewSlug] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] = useState<TicketCategory>("technical");
  const [newTags, setNewTags] = useState("runbook, api");
  const [newContent, setNewContent] = useState("");

  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.listKBArticles({
        category: categoryFilter || undefined,
        limit: 50,
      });
      setArticles(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load KB articles.");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  useEffect(() => {
    void loadArticles();
  }, [loadArticles]);

  const handleSeed = async () => {
    setBusyAction("seed");
    setError(null);
    setBanner(null);
    try {
      const summary = await apiClient.seedKBArticles();
      setBanner(
        `Seeded built-in knowledge base: ${summary.created} created, ${summary.updated} updated (${summary.total} processed).`,
      );
      await loadArticles();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to seed KB articles.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const response = await apiClient.searchKB({
        query: searchQuery.trim(),
        category: searchCategory || null,
        top_k: topK,
        min_score: minScore,
      });
      setSearchHits(response.hits);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Vector search failed.");
    } finally {
      setSearching(false);
    }
  };

  const handleCreateOrUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusyAction("upsert");
    setError(null);
    setBanner(null);
    try {
      const parsedTags = newTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const saved = await apiClient.upsertKBArticle({
        slug: newSlug.trim(),
        title: newTitle.trim(),
        category: newCategory,
        content: newContent.trim(),
        tags: parsedTags,
      });
      setBanner(`Article "${saved.slug}" indexed with fresh vector embedding.`);
      setShowEditor(false);
      setNewSlug("");
      setNewTitle("");
      setNewContent("");
      await loadArticles();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to save KB article.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleDelete = async (article: KBArticle) => {
    setBusyAction(article.id);
    setError(null);
    setBanner(null);
    try {
      await apiClient.deleteKBArticle(article.id);
      setBanner(`Deleted article "${article.slug}".`);
      await loadArticles();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to delete KB article.");
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-mono text-xs font-medium uppercase tracking-wider text-blue-600">
            03 // pgvector RAG Corpus &amp; Similarity Playground
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-slate-900">
            Knowledge Base &amp; Semantic Retrieval
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Seed bilingual runbooks, run cosine similarity queries, and manage indexed RAG articles.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={handleSeed}
            disabled={busyAction !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-600 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-60"
          >
            <Database className="h-3.5 w-3.5" />
            {busyAction === "seed" ? "Seeding..." : "Seed 10 Built-in Articles"}
          </button>

          <button
            type="button"
            onClick={() => setShowEditor((prev) => !prev)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" />
            {showEditor ? "Close Editor" : "Add / Upsert Article"}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {banner && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{banner}</span>
        </div>
      )}

      {showEditor && (
        <form
          onSubmit={handleCreateOrUpdate}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <h3 className="font-display text-base font-semibold text-slate-900">
              Create or Upsert KB Runbook
            </h3>
            <span className="font-mono text-[11px] text-slate-400">
              Matching slug updates existing vector record
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                Slug <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                minLength={3}
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="webhook-retry-backoff"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs text-slate-900 outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                Category <span className="text-red-500">*</span>
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as TicketCategory)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
              >
                {CATEGORY_OPTIONS.map((cat) => (
                  <option key={cat} value={cat}>
                    {formatCategory(cat)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="hmac, retry, webhooks"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              minLength={5}
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Webhook delivery retry policy & HMAC verification"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Runbook Content <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              minLength={20}
              rows={4}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Step-by-step instructions and SLA guidance (minimum 20 characters)..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm leading-relaxed text-slate-900 outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={busyAction !== null}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {busyAction === "upsert" ? "Indexing..." : "Save & Index Article"}
            </button>
          </div>
        </form>
      )}

      {/* Semantic Search Playground */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <h3 className="font-display text-base font-semibold text-slate-900">
              RAG Semantic Vector Search Tester
            </h3>
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            POST /api/v1/kb/search
          </span>
        </div>

        <form onSubmit={handleSearch} className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-12">
          <div className="lg:col-span-6">
            <input
              type="text"
              required
              minLength={2}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter query in RU or EN (e.g. 'webhook hmac 502 error' or 'двойное списание')"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15"
            />
          </div>

          <div className="lg:col-span-2">
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value as TicketCategory | "")}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800"
            >
              <option value="">All Categories</option>
              {CATEGORY_OPTIONS.map((cat) => (
                <option key={cat} value={cat}>
                  {formatCategory(cat)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 lg:col-span-2">
            <label className="font-mono text-xs text-slate-500">TopK</label>
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-16 rounded-lg border border-slate-300 px-2 py-2 font-mono text-xs text-slate-900"
            />
            <label className="font-mono text-xs text-slate-500">Min</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-16 rounded-lg border border-slate-300 px-2 py-2 font-mono text-xs text-slate-900"
            />
          </div>

          <div className="lg:col-span-2">
            <button
              type="submit"
              disabled={searching}
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              <Search className="h-3.5 w-3.5" />
              {searching ? "Searching..." : "Run Search"}
            </button>
          </div>
        </form>

        {searchHits !== null && (
          <div className="mt-4 space-y-2.5 border-t border-slate-100 pt-4">
            <p className="font-mono text-xs font-semibold text-slate-500">
              RETRIEVED {searchHits.length} MATCHING ARTICLE(S)
            </p>
            {searchHits.length === 0 ? (
              <p className="text-xs text-slate-500">
                No hits above score {minScore}. Try seeding articles first or lowering <code className="font-mono">min_score</code>.
              </p>
            ) : (
              searchHits.map((hit) => (
                <div
                  key={hit.article.id}
                  className="rounded-lg border border-blue-200/80 bg-blue-50/40 p-3.5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-blue-600 px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums text-white">
                        Similarity {formatPercent(hit.score)}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-700">
                        {hit.article.slug}
                      </span>
                      <span className="rounded border border-slate-200 bg-white px-2 py-0.5 font-mono text-[10px] uppercase text-slate-600">
                        {formatCategory(hit.article.category)}
                      </span>
                    </div>
                  </div>
                  <h4 className="mt-1.5 text-sm font-semibold text-slate-900">
                    {hit.article.title}
                  </h4>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    {hit.article.content}
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Knowledge Base Corpus */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-slate-700" />
            <h3 className="font-display text-base font-semibold text-slate-900">
              Indexed Corpus ({total})
            </h3>
          </div>

          <select
            aria-label="Filter KB articles by category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as TicketCategory | "")}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
          >
            <option value="">All Categories</option>
            {CATEGORY_OPTIONS.map((cat) => (
              <option key={cat} value={cat}>
                {formatCategory(cat)}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Loading knowledge base articles...
          </p>
        ) : articles.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm font-medium text-slate-700">
              Knowledge base is empty.
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Click <strong>Seed 10 Built-in Articles</strong> above to load bilingual support runbooks and generate embeddings.
            </p>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-3.5 md:grid-cols-2">
            {articles.map((article) => (
              <article
                key={article.id}
                className="flex flex-col justify-between rounded-lg border border-slate-200 bg-slate-50/50 p-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="rounded border border-slate-200 bg-white px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-slate-700">
                        {formatCategory(article.category)}
                      </span>
                      <span className="font-mono text-xs text-blue-700">
                        {article.slug}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => void handleDelete(article)}
                      disabled={busyAction === article.id}
                      title="Delete article"
                      className="rounded p-1 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <h4 className="mt-2 font-display text-sm font-semibold text-slate-900">
                    {article.title}
                  </h4>
                  <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-slate-600">
                    {article.content}
                  </p>
                </div>

                {article.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {article.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-slate-200/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-700"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
