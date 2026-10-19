CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memories (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  memory_type TEXT NOT NULL,
  content TEXT NOT NULL,
  importance NUMERIC(4,3) DEFAULT 0.500,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id, updated_at DESC);

-- AppForge project backup storage.
CREATE TABLE IF NOT EXISTS public.appforge_projects (
  project_id UUID NOT NULL,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL DEFAULT 'Untitled project',
  prompt TEXT NOT NULL DEFAULT '',
  html TEXT NOT NULL DEFAULT '',
  files JSONB NOT NULL DEFAULT '{}'::jsonb,
  versions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, project_id),
  CONSTRAINT appforge_projects_name_length CHECK (char_length(name) <= 80),
  CONSTRAINT appforge_projects_html_length CHECK (octet_length(html) <= 480000)
);

ALTER TABLE public.appforge_projects ADD COLUMN IF NOT EXISTS files JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_appforge_projects_user_updated
  ON public.appforge_projects (user_id, updated_at DESC);

ALTER TABLE public.appforge_projects ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.appforge_projects FROM anon, authenticated;
GRANT ALL ON TABLE public.appforge_projects TO service_role;
