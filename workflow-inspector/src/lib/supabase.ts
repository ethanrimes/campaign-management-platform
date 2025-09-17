// workflow-inspector/src/lib/supabase.ts

import { createClient } from '@supabase/supabase-js'

// Types for our data structures
export interface ExecutionSummary {
  execution_id: string
  initiative_id: string
  workflow_type: string
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  duration_seconds?: number
  campaigns_created: number
  ad_sets_created: number
  posts_created: number
  research_entries: number
  media_files_created: number
  steps_completed?: string[]
  steps_failed?: string[]
  metadata?: Record<string, any>
}

export interface ExecutionData {
  summary: ExecutionSummary
  campaigns: Campaign[]
  adSets: AdSet[]
  posts: Post[]
  research: Research[]
  mediaFiles: MediaFile[]
  logs: ExecutionLog[]
}

export interface Campaign {
  id: string
  initiative_id: string
  name: string
  objective: string
  description?: string
  daily_budget?: number
  lifetime_budget?: number
  start_date?: string
  end_date?: string
  status?: string
  execution_id?: string
  execution_metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface AdSet {
  id: string
  campaign_id: string
  initiative_id: string
  name: string
  objective?: string
  target_audience?: {
    age_range?: number[]
    locations?: string[]
    interests?: string[]
    [key: string]: any
  }
  creative_brief?: {
    theme?: string
    tone?: string
    key_messages?: string[]
    [key: string]: any
  }
  materials?: {
    hashtags?: string[]
    links?: string[]
    [key: string]: any
  }
  daily_budget?: number
  lifetime_budget?: number
  post_frequency?: number
  post_volume?: number
  execution_id?: string
  execution_step?: string
}

export interface Post {
  id: string
  ad_set_id: string
  initiative_id: string
  post_type: string
  text_content?: string
  hashtags?: string[]
  links?: string[]
  media_urls?: string[]
  scheduled_time?: string
  published_time?: string
  facebook_post_id?: string
  instagram_post_id?: string
  status?: string
  is_published?: boolean
  reach?: number
  impressions?: number
  engagement?: number
  clicks?: number
  comments_count?: number
  shares?: number
  execution_id?: string
  execution_step?: string
}

export interface Research {
  id: string
  initiative_id: string
  research_type: string
  topic: string
  summary?: string
  insights?: Array<{
    topic?: string
    finding: string
    source?: string
    relevance_score?: number
  }>
  raw_data?: {
    recommended_hashtags?: string[]
    content_opportunities?: Array<{
      type?: string
      description: string
      priority?: string
    }>
    [key: string]: any
  }
  sources?: string[]
  execution_id?: string
  execution_step?: string
  created_at: string
}

export interface MediaFile {
  id: string
  initiative_id: string
  file_type: string
  public_url: string
  supabase_path: string
  prompt_used?: string
  dimensions?: { width: number; height: number }
  duration_seconds?: number
  execution_id?: string
  execution_step?: string
  created_at: string
}

export interface ExecutionLog {
  id: string
  execution_id: string
  initiative_id: string
  workflow_type: string
  status: string
  started_at: string
  completed_at?: string
  steps_completed?: string[]
  steps_failed?: string[]
  error_messages?: Record<string, any>
  metadata?: Record<string, any>
}

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Fetch execution summaries
export async function getExecutionSummaries(): Promise<ExecutionSummary[]> {
  try {
    const { data, error } = await supabase
      .from('execution_summary')
      .select('*')
      .order('started_at', { ascending: false })
      .limit(50)

    if (error) throw error
    return data || []
  } catch (error) {
    console.error('Error fetching execution summaries:', error)
    return []
  }
}

// Fetch complete execution details
export async function getExecutionDetails(executionId: string): Promise<ExecutionData> {
  try {
    // Fetch all data in parallel for better performance
    const [
      summaryResult,
      campaignsResult,
      adSetsResult,
      postsResult,
      researchResult,
      mediaFilesResult,
      logsResult
    ] = await Promise.all([
      // Fetch summary
      supabase
        .from('execution_summary')
        .select('*')
        .eq('execution_id', executionId)
        .single(),
      
      // Fetch campaigns
      supabase
        .from('campaigns')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false }),
      
      // Fetch ad sets
      supabase
        .from('ad_sets')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false }),
      
      // Fetch posts
      supabase
        .from('posts')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false }),
      
      // Fetch research
      supabase
        .from('research')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false }),
      
      // Fetch media files
      supabase
        .from('media_files')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false }),
      
      // Fetch execution logs
      supabase
        .from('execution_logs')
        .select('*')
        .eq('execution_id', executionId)
        .order('created_at', { ascending: false })
    ])

    // Check for errors
    if (summaryResult.error) throw summaryResult.error
    if (!summaryResult.data) throw new Error('Execution not found')

    return {
      summary: summaryResult.data,
      campaigns: campaignsResult.data || [],
      adSets: adSetsResult.data || [],
      posts: postsResult.data || [],
      research: researchResult.data || [],
      mediaFiles: mediaFilesResult.data || [],
      logs: logsResult.data || []
    }
  } catch (error) {
    console.error('Error fetching execution details:', error)
    throw error
  }
}

// Subscribe to real-time updates for running executions
export function subscribeToExecution(
  executionId: string,
  onUpdate: (data: any) => void
) {
  const subscription = supabase
    .channel(`execution:${executionId}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'execution_logs',
        filter: `execution_id=eq.${executionId}`
      },
      (payload) => {
        console.log('Execution update:', payload)
        onUpdate(payload)
      }
    )
    .subscribe()

  return () => {
    subscription.unsubscribe()
  }
}

// Export the raw client for advanced usage
export { supabase }