'use client'

import { useState, useEffect } from 'react'
import { getExecutionSummaries, getExecutionDetails } from '@/lib/supabase'
import { ExecutionSummary, ExecutionData } from '@/lib/types'
import ExecutionSelector from '@/components/ExecutionSelector'
import ExecutionTimeline from '@/components/ExecutionTimeline'
import ResearchDisplay from '@/components/ResearchDisplay'
import PlanDisplay from '@/components/PlanDisplay'
import ContentDisplay from '@/components/ContentDisplay'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, Activity, FileSearch, Layout, PenTool } from 'lucide-react'

export default function WorkflowInspector() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([])
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>('')
  const [executionData, setExecutionData] = useState<ExecutionData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingExecutions, setLoadingExecutions] = useState(true)

  // Load execution summaries on mount
  useEffect(() => {
    loadExecutions()
  }, [])

  // Load execution details when selection changes
  useEffect(() => {
    if (selectedExecutionId) {
      loadExecutionDetails(selectedExecutionId)
    }
  }, [selectedExecutionId])

  async function loadExecutions() {
    setLoadingExecutions(true)
    try {
      const summaries = await getExecutionSummaries()
      setExecutions(summaries)
      
      // Auto-select the most recent execution if available
      if (summaries.length > 0 && !selectedExecutionId) {
        setSelectedExecutionId(summaries[0].execution_id)
      }
    } catch (error) {
      console.error('Failed to load executions:', error)
    } finally {
      setLoadingExecutions(false)
    }
  }

  async function loadExecutionDetails(executionId: string) {
    setLoading(true)
    try {
      const data = await getExecutionDetails(executionId)
      setExecutionData(data)
    } catch (error) {
      console.error('Failed to load execution details:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Activity className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Workflow Inspector</h1>
                <p className="text-sm text-gray-500">Campaign execution trace viewer</p>
              </div>
            </div>
            <button
              onClick={loadExecutions}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Execution Selector */}
        <div className="mb-8">
          <ExecutionSelector
            executions={executions}
            selectedExecutionId={selectedExecutionId}
            onSelectExecution={setSelectedExecutionId}
            loading={loadingExecutions}
          />
        </div>

        {/* Timeline */}
        {executionData && (
          <div className="mb-8">
            <ExecutionTimeline executionData={executionData} />
          </div>
        )}

        {/* Main Content Area */}
        {loading ? (
          <div className="flex items-center justify-center h-64 bg-white rounded-lg shadow">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : executionData ? (
          <Tabs defaultValue="research" className="space-y-4">
            <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
              <TabsTrigger value="research" className="flex items-center gap-2">
                <FileSearch className="h-4 w-4" />
                Research
              </TabsTrigger>
              <TabsTrigger value="plan" className="flex items-center gap-2">
                <Layout className="h-4 w-4" />
                Planning
              </TabsTrigger>
              <TabsTrigger value="content" className="flex items-center gap-2">
                <PenTool className="h-4 w-4" />
                Content
              </TabsTrigger>
            </TabsList>

            <TabsContent value="research" className="space-y-4">
              <ResearchDisplay research={executionData.research} />
            </TabsContent>

            <TabsContent value="plan" className="space-y-4">
              <PlanDisplay 
                campaigns={executionData.campaigns}
                adSets={executionData.adSets}
              />
            </TabsContent>

            <TabsContent value="content" className="space-y-4">
              <ContentDisplay 
                posts={executionData.posts}
                mediaFiles={executionData.mediaFiles}
              />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex items-center justify-center h-64 bg-white rounded-lg shadow">
            <p className="text-gray-500">Select an execution to view details</p>
          </div>
        )}
      </main>
    </div>
  )
}