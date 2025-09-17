// Database Types based on your models

// workflow-inspector/src/lib/types.ts

// Re-export all types from supabase.ts for backward compatibility
export type {
  ExecutionSummary,
  ExecutionData,
  Campaign,
  AdSet,
  Post,
  Research,
  MediaFile,
  ExecutionLog
} from './supabase'

// export interface ExecutionLog {
//   id: string;
//   execution_id: string;
//   initiative_id: string;
//   workflow_type: string;
//   status: 'running' | 'completed' | 'failed';
//   started_at: string;
//   completed_at?: string;
//   steps_completed?: string[];
//   steps_failed?: string[];
//   error_messages?: Record<string, any>;
//   metadata?: Record<string, any>;
//   created_at?: string;
//   updated_at?: string;
// }

// export interface ExecutionSummary {
//   execution_id: string;
//   initiative_id: string;
//   workflow_type: string;
//   status: string;
//   started_at: string;
//   completed_at?: string;
//   duration_seconds?: number;
//   campaigns_created: number;
//   ad_sets_created: number;
//   posts_created: number;
//   research_entries: number;
//   media_files_created: number;
//   steps_completed?: string[];
//   steps_failed?: string[];
//   metadata?: Record<string, any>;
// }

// export interface Campaign {
//   id: string;
//   initiative_id: string;
//   name: string;
//   objective: string;
//   description?: string;
//   budget_mode?: string;
//   daily_budget?: number;
//   lifetime_budget?: number;
//   spent_budget?: number;
//   start_date?: string;
//   end_date?: string;
//   status?: string;
//   is_active?: boolean;
//   metrics?: Record<string, any>;
//   execution_id?: string;
//   execution_metadata?: Record<string, any>;
//   created_at?: string;
//   updated_at?: string;
// }

// export interface AdSet {
//   id: string;
//   initiative_id: string;
//   campaign_id: string;
//   name: string;
//   objective?: string;
//   target_audience?: Record<string, any>;
//   placements?: Record<string, any>;
//   daily_budget?: number;
//   lifetime_budget?: number;
//   creative_brief?: Record<string, any>;
//   materials?: Record<string, any>;
//   post_frequency?: number;
//   post_volume?: number;
//   status?: string;
//   execution_id?: string;
//   execution_step?: string;
//   created_at?: string;
//   updated_at?: string;
// }

// export interface Post {
//   id: string;
//   initiative_id: string;
//   ad_set_id: string;
//   post_type: string;
//   text_content?: string;
//   hashtags?: string[];
//   links?: string[];
//   media_urls?: string[];
//   media_metadata?: Record<string, any>;
//   scheduled_time?: string;
//   published_time?: string;
//   facebook_post_id?: string;
//   instagram_post_id?: string;
//   status?: string;
//   is_published?: boolean;
//   reach?: number;
//   impressions?: number;
//   engagement?: number;
//   execution_id?: string;
//   execution_step?: string;
//   generation_metadata?: Record<string, any>;
//   created_at?: string;
//   updated_at?: string;
//   comments_count?: number;
//   shares?: number;
// }

// export interface Research {
//   id: string;
//   initiative_id: string;
//   research_type: string;
//   topic: string;
//   summary?: string;
//   insights?: Array<Record<string, any>>;
//   raw_data?: Record<string, any>;
//   sources?: string[];
//   search_queries?: string[];
//   relevance_score?: Record<string, any>;
//   tags?: string[];
//   execution_id?: string;
//   execution_step?: string;
//   created_at?: string;
//   expires_at?: string;
// }

// export interface MediaFile {
//   id: string;
//   initiative_id: string;
//   file_type: 'image' | 'video' | 'reel' | 'carousel';
//   supabase_path: string;
//   public_url: string;
//   prompt_used?: string;
//   dimensions?: Record<string, number>;
//   duration_seconds?: number;
//   file_size_bytes?: number;
//   metadata?: Record<string, any>;
//   execution_id?: string;
//   execution_step?: string;
//   created_at?: string;
//   updated_at?: string;
// }

// export interface ExecutionData {
//   summary: ExecutionSummary;
//   campaigns: Campaign[];
//   adSets: AdSet[];
//   posts: Post[];
//   research: Research[];
//   mediaFiles: MediaFile[];
// }