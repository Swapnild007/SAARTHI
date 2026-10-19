-- AppForge project backup storage.
-- Apply with the existing SAARTHI Supabase service-role setup.
CREATE TABLE IF NOT EXISTS public.appforge_projects (
  project_id UUID NOT NULL,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL DEFAULT 'Untitled project',
  prompt TEXT NOT NULL DEFAULT '',
  html TEXT NOT NULL DEFAULT '',
  versions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, project_id),
  CONSTRAINT appforge_projects_name_length CHECK (char_length(name) <= 80),
  CONSTRAINT appforge_projects_html_length CHECK (octet_length(html) <= 480000)
);

CREATE INDEX IF NOT EXISTS idx_appforge_projects_user_updated
  ON public.appforge_projects (user_id, updated_at DESC);

ALTER TABLE public.appforge_projects ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.appforge_projects FROM anon, authenticated;
GRANT ALL ON TABLE public.appforge_projects TO service_role;
