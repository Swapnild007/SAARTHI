-- SAARTHI managed RAG storage. Run once in the Supabase SQL editor.
-- Default embedding dimension is 1536; use the matching embedding model.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
  id TEXT PRIMARY KEY,
  collection TEXT NOT NULL DEFAULT 'default',
  title TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT '',
  chunk_index INTEGER NOT NULL DEFAULT 0,
  content TEXT NOT NULL,
  embedding VECTOR(1536) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saarthi_knowledge_collection
  ON public.knowledge_chunks (collection);
CREATE INDEX IF NOT EXISTS idx_saarthi_knowledge_embedding
  ON public.knowledge_chunks USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION public.match_saarthi_knowledge(
  query_embedding VECTOR(1536),
  match_count INTEGER DEFAULT 5,
  filter_collection TEXT DEFAULT 'default'
)
RETURNS TABLE (
  id TEXT, collection TEXT, title TEXT, source TEXT, chunk_index INTEGER,
  content TEXT, similarity DOUBLE PRECISION
)
LANGUAGE SQL STABLE
AS $$
  SELECT k.id, k.collection, k.title, k.source, k.chunk_index, k.content,
         1 - (k.embedding <=> query_embedding) AS similarity
  FROM public.knowledge_chunks AS k
  WHERE k.collection = filter_collection
  ORDER BY k.embedding <=> query_embedding
  LIMIT LEAST(GREATEST(match_count, 1), 8);
$$;

-- Backend service-role credentials are server-side only. Never expose them to the browser.

ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.knowledge_chunks FROM anon, authenticated;
GRANT ALL ON public.knowledge_chunks TO service_role;
REVOKE ALL ON FUNCTION public.match_saarthi_knowledge(VECTOR, INTEGER, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_saarthi_knowledge(VECTOR, INTEGER, TEXT) TO service_role;
