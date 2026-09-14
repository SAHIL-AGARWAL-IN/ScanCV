-- Supabase Database Schema for ScanCV ATS Resume Scorer

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create analyses table
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    ats_score INTEGER DEFAULT 0,
    keyword_match INTEGER DEFAULT 0,
    missing_keywords JSONB DEFAULT '[]'::jsonb,
    analysis_result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON public.analyses(created_at DESC);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies
-- Users can only read their own analyses
CREATE POLICY "Users can view their own analyses"
ON public.analyses
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own analyses
CREATE POLICY "Users can insert their own analyses"
ON public.analyses
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can delete their own analyses
CREATE POLICY "Users can delete their own analyses"
ON public.analyses
FOR DELETE
USING (auth.uid() = user_id);

-- Service role bypasses RLS automatically (used by backend SUPABASE_KEY)
