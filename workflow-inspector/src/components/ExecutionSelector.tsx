// workflow-inspector/src/components/ExecutionSelector.tsx

'use client'

import { ExecutionSummary } from '@/lib/types'
import { formatDistanceToNow, format } from 'date-fns'
import { 
  Search, 
  Calendar, 
  Activity, 
  CheckCircle, 
  XCircle, 
  Loader2,
  ChevronDown,
  Clock,
  BarChart3,
  Hash,
  FileText
} from 'lucide-react'
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
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
      default:
        return <Activity className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 text-green-800 border-green-200'
      case 'failed':
        return 'bg-red-50 text-red-800 border-red-200'
      case 'running':
        return 'bg-blue-50 text-blue-800 border-blue-200'
      default:
        return 'bg-gray-50 text-gray-800 border-gray-200'
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-gradient-to-r from-green-500 to-green-600 text-white'
      case 'failed':
        return 'bg-gradient-to-r from-red-500 to-red-600 text-white'
      case 'running':
        return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white animate-pulse'
      default:
        return 'bg-gradient-to-r from-gray-500 to-gray-600 text-white'
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100">
      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Execution Selector</h2>
            <p className="text-gray-600 mt-1">Choose a workflow execution to inspect</p>
          </div>
          {selectedExecution && (
            <div className={`px-4 py-2 rounded-full text-sm font-semibold ${getStatusBadgeColor(selectedExecution.status)}`}>
              {selectedExecution.status.toUpperCase()}
            </div>
          )}
        </div>
        
        {/* Search and Dropdown */}
        <div className="relative">
          {/* Selected Value Display */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-full px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-xl text-left hover:from-gray-100 hover:to-gray-150 transition-all shadow-sm hover:shadow-md"
            disabled={loading}
          >
            {loading ? (
              <div className="flex items-center space-x-3">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                <span className="text-gray-600 text-lg">Loading executions...</span>
              </div>
            ) : selectedExecution ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getStatusIcon(selectedExecution.status)}
                  <div>
                    <div className="font-semibold text-gray-900 text-lg">
                      {format(new Date(selectedExecution.started_at), 'PPpp')}
                    </div>
                    <div className="text-gray-600 flex items-center gap-3 mt-1">
                      <span className="font-medium">{selectedExecution.workflow_type}</span>
                      <span className="text-gray-400">•</span>
                      <span className="font-mono text-sm">ID: {selectedExecution.execution_id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </div>
                <ChevronDown className={`h-6 w-6 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-gray-500 text-lg">Select an execution...</span>
                <ChevronDown className="h-6 w-6 text-gray-400" />
              </div>
            )}
          </button>

          {/* Dropdown */}
          {isOpen && !loading && (
            <div className="absolute z-20 mt-3 w-full bg-white border border-gray-200 rounded-xl shadow-xl max-h-[500px] overflow-hidden">
              {/* Search Bar */}
              <div className="p-4 border-b bg-gray-50">
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by ID, type, or timestamp..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              </div>

              {/* Execution List */}
              <div className="max-h-96 overflow-y-auto">
                {filteredExecutions.length > 0 ? (
                  filteredExecutions.map((exec) => (
                    <button
                      key={exec.execution_id}
                      onClick={() => {
                        onSelectExecution(exec.execution_id)
                        setIsOpen(false)
                        setSearchTerm('')
                      }}
                      className={`w-full px-6 py-4 text-left hover:bg-gray-50 transition-colors border-b last:border-b-0 ${
                        exec.execution_id === selectedExecutionId ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          {getStatusIcon(exec.status)}
                          <div>
                            <div className="font-semibold text-gray-900 text-base">
                              {format(new Date(exec.started_at), 'PPp')}
                            </div>
                            <div className="text-sm text-gray-600 mt-1 flex items-center gap-2">
                              <span className="font-medium">{exec.workflow_type}</span>
                              <span className="text-gray-400">•</span>
                              <Clock className="h-3 w-3" />
                              <span>{formatDistanceToNow(new Date(exec.started_at), { addSuffix: true })}</span>
                            </div>
                            <div className="text-xs text-gray-500 mt-1 font-mono">
                              ID: {exec.execution_id}
                            </div>
                          </div>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(exec.status)}`}>
                          {exec.status}
                        </div>
                      </div>
                      
                      {/* Stats */}
                      <div className="flex items-center space-x-6 text-sm text-gray-600 pl-8">
                        <div className="flex items-center gap-1">
                          <BarChart3 className="h-4 w-4 text-gray-400" />
                          <span className="font-medium">{exec.campaigns_created}</span>
                          <span>campaigns</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <FileText className="h-4 w-4 text-gray-400" />
                          <span className="font-medium">{exec.posts_created}</span>
                          <span>posts</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Hash className="h-4 w-4 text-gray-400" />
                          <span className="font-medium">{exec.research_entries}</span>
                          <span>research</span>
                        </div>
                        {exec.duration_seconds && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-4 w-4 text-gray-400" />
                            <span className="font-medium">{Math.round(exec.duration_seconds / 60)}m</span>
                            <span>duration</span>
                          </div>
                        )}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="px-6 py-12 text-center text-gray-500">
                    <Search className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-lg">No executions found</p>
                    <p className="text-sm mt-1">Try adjusting your search</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Quick Stats Cards */}
        {selectedExecution && (
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-200">
              <div className="flex items-center justify-between mb-2">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                <span className="text-2xl font-bold text-gray-900">
                  {selectedExecution.campaigns_created}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-700">Campaigns</div>
            </div>
            
            <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
              <div className="flex items-center justify-between mb-2">
                <Layout className="h-5 w-5 text-purple-600" />
                <span className="text-2xl font-bold text-gray-900">
                  {selectedExecution.ad_sets_created}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-700">Ad Sets</div>
            </div>
            
            <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-4 border border-green-200">
              <div className="flex items-center justify-between mb-2">
                <FileText className="h-5 w-5 text-green-600" />
                <span className="text-2xl font-bold text-gray-900">
                  {selectedExecution.posts_created}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-700">Posts</div>
            </div>
            
            <div className="bg-gradient-to-r from-orange-50 to-orange-100 rounded-xl p-4 border border-orange-200">
              <div className="flex items-center justify-between mb-2">
                <Image className="h-5 w-5 text-orange-600" />
                <span className="text-2xl font-bold text-gray-900">
                  {selectedExecution.media_files_created}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-700">Media Files</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Missing imports
import { Layout, Image } from 'lucide-react'