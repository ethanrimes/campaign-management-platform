// workflow-inspector/src/app/page.tsx (Updated to use API)

'use client'

import { useState, useEffect } from 'react'
import { ExecutionSummary, ExecutionData } from '@/lib/types'
import { getExecutionSummaries, getExecutionDetails, subscribeToExecution } from '@/lib/api'  // Use API instead of Supabase
import ExecutionSelector from '@/components/ExecutionSelector'
import ExecutionTimeline from '@/components/ExecutionTimeline'
import ResearchDisplay from '@/components/ResearchDisplay'
import PlanDisplay from '@/components/PlanDisplay'
import ContentDisplay from '@/components/ContentDisplay'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, Activity, FileSearch, Layout, PenTool, RefreshCw, AlertCircle } from 'lucide-react'

export default function WorkflowInspector() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([])
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>('')
  const [executionData, setExecutionData] = useState<ExecutionData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingExecutions, setLoadingExecutions] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('research')

  // Load execution summaries on mount
  useEffect(() => {
    loadExecutions()
  }, [])

  // Load execution details when selection changes
  useEffect(() => {
    if (selectedExecutionId) {
      loadExecutionDetails(selectedExecutionId)
      
      // Subscribe to real-time updates if execution is running
      const currentExecution = executions.find(e => e.execution_id === selectedExecutionId)
      if (currentExecution?.status === 'running') {
        const unsubscribe = subscribeToExecution(selectedExecutionId, () => {
          // Reload execution details on updates
          loadExecutionDetails(selectedExecutionId)
        })
        
        return () => {
          unsubscribe()
        }
      }
    }
  }, [selectedExecutionId, executions])

  async function loadExecutions() {
    setLoadingExecutions(true)
    setError(null)
    try {
      const summaries = await getExecutionSummaries()
      setExecutions(summaries)
      
      // Auto-select the most recent execution if available
      if (summaries.length > 0 && !selectedExecutionId) {
        setSelectedExecutionId(summaries[0].execution_id)
      }
    } catch (error) {
      console.error('Failed to load executions:', error)
      setError('Failed to load executions. Please check your connection and ensure the API is running.')
    } finally {
      setLoadingExecutions(false)
    }
  }

  async function loadExecutionDetails(executionId: string) {
    setLoading(true)
    setError(null)
    try {
      const data = await getExecutionDetails(executionId)
      setExecutionData(data)
      
      // Update the execution in the list with the latest summary
      if (data.summary) {
        setExecutions(prev => prev.map(e => 
          e.execution_id === executionId 
            ? { ...e, ...data.summary }
            : e
        ))
      }
    } catch (error) {
      console.error('Failed to load execution details:', error)
      setError('Failed to load execution details. Please try again.')
      setExecutionData(null)
    } finally {
      setLoading(false)
    }
  }

  const refreshData = () => {
    loadExecutions()
    if (selectedExecutionId) {
      loadExecutionDetails(selectedExecutionId)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Enhanced Header */}
      <header className="bg-white shadow-lg border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl shadow-md">
                <Activity className="h-10 w-10 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                  Workflow Inspector
                </h1>
                <p className="text-base text-gray-600 mt-1">
                  Campaign execution trace viewer
                </p>
              </div>
            </div>
            <button
              onClick={refreshData}
              className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all shadow-md hover:shadow-lg font-medium"
              disabled={loading || loadingExecutions}
            >
              <RefreshCw className={`h-5 w-5 ${(loading || loadingExecutions) ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-red-800">{error}</p>
              <p className="text-sm text-red-600 mt-1">
                Make sure the backend API is running on http://localhost:8000
              </p>
            </div>
          </div>
        )}

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
        {executionData && !loading && (
          <div className="mb-8 animate-in slide-in-from-bottom-4 duration-500">
            <ExecutionTimeline executionData={executionData} />
          </div>
        )}

        {/* Main Content Area */}
        {loading ? (
          <div className="flex flex-col items-center justify-center h-96 bg-white rounded-2xl shadow-lg">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-lg text-gray-600">Loading execution details...</p>
          </div>
        ) : executionData ? (
          <div className="animate-in slide-in-from-bottom-4 duration-500">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="grid w-full grid-cols-3 lg:w-[500px] mx-auto h-14 p-1 bg-gray-100/80 backdrop-blur">
                <TabsTrigger 
                  value="research" 
                  className="flex items-center gap-2 text-base font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm"
                >
                  <FileSearch className="h-5 w-5" />
                  <span>Research</span>
                </TabsTrigger>
                <TabsTrigger 
                  value="plan" 
                  className="flex items-center gap-2 text-base font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm"
                >
                  <Layout className="h-5 w-5" />
                  <span>Planning</span>
                </TabsTrigger>
                <TabsTrigger 
                  value="content" 
                  className="flex items-center gap-2 text-base font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm"
                >
                  <PenTool className="h-5 w-5" />
                  <span>Content</span>
                </TabsTrigger>
              </TabsList>

              <div className="bg-white rounded-2xl shadow-lg p-8">
                <TabsContent value="research" className="mt-0 space-y-6">
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Research Insights</h2>
                    <p className="text-gray-600">Market analysis and trend discovery</p>
                  </div>
                  <ResearchDisplay research={executionData.research} />
                </TabsContent>

                <TabsContent value="plan" className="mt-0 space-y-6">
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Campaign Strategy</h2>
                    <p className="text-gray-600">Campaigns and ad set configuration</p>
                  </div>
                  <PlanDisplay 
                    campaigns={executionData.campaigns}
                    adSets={executionData.adSets}
                  />
                </TabsContent>

                <TabsContent value="content" className="mt-0 space-y-6">
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Generated Content</h2>
                    <p className="text-gray-600">Posts and media created for campaigns</p>
                  </div>
                  <ContentDisplay 
                    posts={executionData.posts}
                    mediaFiles={executionData.mediaFiles}
                  />
                </TabsContent>
              </div>
            </Tabs>
          </div>
        ) : !loadingExecutions && executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-96 bg-white rounded-2xl shadow-lg">
            <Activity className="h-16 w-16 text-gray-300 mb-4" />
            <p className="text-xl text-gray-600 font-medium">No Executions Found</p>
            <p className="text-gray-500 mt-2">Run a workflow to see execution traces here</p>
            <p className="text-sm text-gray-400 mt-4">
              Make sure the API is running and accessible
            </p>
          </div>
        ) : !selectedExecutionId && !loadingExecutions ? (
          <div className="flex flex-col items-center justify-center h-96 bg-white rounded-2xl shadow-lg">
            <FileSearch className="h-16 w-16 text-gray-300 mb-4" />
            <p className="text-xl text-gray-600 font-medium">Select an Execution</p>
            <p className="text-gray-500 mt-2">Choose an execution from the dropdown above to view details</p>
          </div>
        ) : null}
      </main>
    </div>
  )
}