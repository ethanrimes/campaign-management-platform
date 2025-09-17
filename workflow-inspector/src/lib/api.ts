// workflow-inspector/src/lib/api.ts

import { ExecutionSummary, ExecutionData } from './types'

// Configure API base URL - update this to match your backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export class ExecutionAPI {
  /**
   * Fetch execution summaries for the dropdown
   */
  static async getExecutionSummaries(initiativeId?: string): Promise<ExecutionSummary[]> {
    try {
      const params = new URLSearchParams()
      if (initiativeId) {
        params.append('initiative_id', initiativeId)
      }
      params.append('limit', '50')

      const response = await fetch(`${API_BASE_URL}/executions/summaries?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch summaries: ${response.statusText}`)
      }

      const data = await response.json()
      return data as ExecutionSummary[]
    } catch (error) {
      console.error('Failed to fetch execution summaries:', error)
      throw error
    }
  }

  /**
   * Fetch complete execution details
   */
  static async getExecutionDetails(executionId: string): Promise<ExecutionData> {
    try {
      const response = await fetch(`${API_BASE_URL}/executions/${executionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Execution not found')
        }
        throw new Error(`Failed to fetch execution details: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Transform the data to match the expected frontend format
      return {
        summary: data.summary,
        campaigns: data.campaigns || [],
        adSets: data.adSets || [],
        posts: data.posts || [],
        research: data.research || [],
        mediaFiles: data.mediaFiles || [],
        logs: data.logs || []
      }
    } catch (error) {
      console.error('Failed to fetch execution details:', error)
      throw error
    }
  }

  /**
   * Subscribe to real-time updates for an execution (placeholder for future WebSocket implementation)
   */
  static subscribeToExecution(executionId: string, callback: () => void): () => void {
    // For now, just poll every 5 seconds if execution is running
    let intervalId: NodeJS.Timeout | null = null

    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/executions/${executionId}/summary`)
        const summary = await response.json()
        
        if (summary.status === 'running') {
          callback()
        } else if (intervalId) {
          clearInterval(intervalId)
        }
      } catch (error) {
        console.error('Failed to check execution status:', error)
      }
    }

    // Start polling
    intervalId = setInterval(checkStatus, 5000)

    // Return cleanup function
    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }
}

// Export convenience functions that match the old interface
export const getExecutionSummaries = ExecutionAPI.getExecutionSummaries
export const getExecutionDetails = ExecutionAPI.getExecutionDetails
export const subscribeToExecution = ExecutionAPI.subscribeToExecution