import { createClient } from '@supabase/supabase-js'
import type { 
  ExecutionLog, 
  ExecutionSummary, 
  Campaign, 
  AdSet, 
  Post, 
  Research, 
  MediaFile,
  ExecutionData 
} from './types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// API Functions
export async function getExecutionSummaries(initiativeId?: string) {
  let query = supabase
    .from('execution_summary')
    .select('*')
    .order('started_at', { ascending: false })

  if (initiativeId) {
    query = query.eq('initiative_id', initiativeId)
  }

  const { data, error } = await query
  
  if (error) {
    console.error('Error fetching execution summaries:', error)
    return []
  }
  
  return data as ExecutionSummary[]
}

export async function getExecutionDetails(executionId: string): Promise<ExecutionData | null> {
  try {
    // Fetch all related data in parallel
    const [
      summaryResult,
      campaignsResult,
      adSetsResult,
      postsResult,
      researchResult,
      mediaFilesResult
    ] = await Promise.all([
      supabase
        .from('execution_summary')
        .select('*')
        .eq('execution_id', executionId)
        .single(),
      supabase
        .from('campaigns')
        .select('*')
        .eq('execution_id', executionId),
      supabase
        .from('ad_sets')
        .select('*')
        .eq('execution_id', executionId),
      supabase
        .from('posts')
        .select('*')
        .eq('execution_id', executionId),
      supabase
        .from('research')
        .select('*')
        .eq('execution_id', executionId),
      supabase
        .from('media_files')
        .select('*')
        .eq('execution_id', executionId)
    ])

    if (summaryResult.error) {
      console.error('Error fetching execution summary:', summaryResult.error)
      return null
    }

    return {
      summary: summaryResult.data as ExecutionSummary,
      campaigns: (campaignsResult.data || []) as Campaign[],
      adSets: (adSetsResult.data || []) as AdSet[],
      posts: (postsResult.data || []) as Post[],
      research: (researchResult.data || []) as Research[],
      mediaFiles: (mediaFilesResult.data || []) as MediaFile[]
    }
  } catch (error) {
    console.error('Error fetching execution details:', error)
    return null
  }
}

// Real-time subscription for execution updates
export function subscribeToExecutionUpdates(
  executionId: string,
  callback: (payload: any) => void
) {
  return supabase
    .channel(`execution_${executionId}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'execution_logs',
        filter: `execution_id=eq.${executionId}`
      },
      callback
    )
    .subscribe()
}