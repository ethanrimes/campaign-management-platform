'use client'

import { ExecutionSummary } from '@/lib/types'
import { formatDistanceToNow, format } from 'date-fns'
import { Search, Calendar, Activity, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { useState, useMemo } from 'react'

interface ExecutionSelectorProps {
  executions: ExecutionSummary[]
  selectedExecutionId: string
  onSelectExecution: (executionId: string) => void
  loading: boolean
}

export default function ExecutionSelector({
  executions,
  selectedExecutionId,
  onSelectExecution,
  loading
}: ExecutionSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  // Filter and sort executions
  const filteredExecutions = useMemo(() => {
    return executions.filter(exec => {
      const searchLower = searchTerm.toLowerCase()
      const timestamp = format(new Date(exec.started_at), 'PPpp')
      return (
        exec.execution_id.toLowerCase().includes(searchLower) ||
        exec.workflow_type.toLowerCase().includes(searchLower) ||
        timestamp.toLowerCase().includes(searchLower)
      )
    })
  }, [executions, searchTerm])

  const selectedExecution = executions.find(e => e.execution_id === selectedExecutionId)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Activity className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 text-green-700 border-green-200'
      case 'failed':
        return 'bg-red-50 text-red-700 border-red-200'
      case 'running':
        return 'bg-blue-50 text-blue-700 border-blue-200'
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div className="p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Execution Selector</h2>
        
        {/* Search and Dropdown */}
        <div className="relative">
          {/* Selected Value Display */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-left hover:bg-gray-100 transition-colors"
            disabled={loading}
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-gray-500">Loading executions...</span>
              </div>
            ) : selectedExecution ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(selectedExecution.status)}
                  <div>
                    <div className="font-medium text-gray-900">
                      {format(new Date(selectedExecution.started_at), 'PPpp')}
                    </div>
                    <div className="text-sm text-gray-500">
                      {selectedExecution.workflow_type} • {selectedExecution.execution_id.slice(0, 8)}...
                    </div>
                  </div>
                </div>
                <Calendar className="h-4 w-4 text-gray-400" />
              </div>
            ) : (
              <span className="text-gray-500">Select an execution...</span>
            )}
          </button>

          {/* Dropdown */}
          {isOpen && !loading && (
            <div className="absolute z-10 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden">
              {/* Search Bar */}
              <div className="p-3 border-b">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by ID, type, or timestamp..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Execution List */}
              <div className="max-h-64 overflow-y-auto">
                {filteredExecutions.length > 0 ? (
                  filteredExecutions.map((exec) => (
                    <button
                      key={exec.execution_id}
                      onClick={() => {
                        onSelectExecution(exec.execution_id)
                        setIsOpen(false)
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b last:border-b-0 ${
                        exec.execution_id === selectedExecutionId ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          {getStatusIcon(exec.status)}
                          <div>
                            <div className="font-medium text-gray-900">
                              {format(new Date(exec.started_at), 'PPp')}
                            </div>
                            <div className="text-sm text-gray-500">
                              {exec.workflow_type} • {formatDistanceToNow(new Date(exec.started_at), { addSuffix: true })}
                            </div>
                            <div className="text-xs text-gray-400 mt-1">
                              ID: {exec.execution_id}
                            </div>
                          </div>
                        </div>
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(exec.status)}`}>
                          {exec.status}
                        </div>
                      </div>
                      
                      {/* Stats */}
                      <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                        <span>{exec.campaigns_created} campaigns</span>
                        <span>{exec.posts_created} posts</span>
                        <span>{exec.research_entries} research</span>
                        {exec.duration_seconds && (
                          <span>{Math.round(exec.duration_seconds / 60)}m duration</span>
                        )}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-8 text-center text-gray-500">
                    No executions found
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Quick Stats */}
        {selectedExecution && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Campaigns</div>
              <div className="text-lg font-semibold text-gray-900">
                {selectedExecution.campaigns_created}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Ad Sets</div>
              <div className="text-lg font-semibold text-gray-900">
                {selectedExecution.ad_sets_created}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Posts</div>
              <div className="text-lg font-semibold text-gray-900">
                {selectedExecution.posts_created}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Media Files</div>
              <div className="text-lg font-semibold text-gray-900">
                {selectedExecution.media_files_created}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}