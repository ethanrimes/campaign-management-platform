'use client'

import { ExecutionData } from '@/lib/types'
import { formatDistanceStrict } from 'date-fns'
import { 
  CheckCircle, 
  XCircle, 
  Clock,
  FileSearch,
  Layout,
  PenTool,
  Loader2
} from 'lucide-react'

interface ExecutionTimelineProps {
  executionData: ExecutionData
}

export default function ExecutionTimeline({ executionData }: ExecutionTimelineProps) {
  const { summary } = executionData
  
  const steps = [
    {
      name: 'Research',
      icon: FileSearch,
      status: summary.steps_completed?.includes('Research') ? 'completed' : 
              summary.steps_failed?.includes('Research') ? 'failed' : 
              'pending',
      count: summary.research_entries,
      description: 'Gathering market insights and trends'
    },
    {
      name: 'Planning',
      icon: Layout,
      status: summary.steps_completed?.includes('Planning') ? 'completed' : 
              summary.steps_failed?.includes('Planning') ? 'failed' : 
              'pending',
      count: summary.campaigns_created + summary.ad_sets_created,
      description: 'Creating campaign strategy and ad sets'
    },
    {
      name: 'Content Creation',
      icon: PenTool,
      status: summary.steps_completed?.includes('Content Creation') ? 'completed' : 
              summary.steps_failed?.includes('Content Creation') ? 'failed' : 
              'pending',
      count: summary.posts_created + summary.media_files_created,
      description: 'Generating posts and media content'
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-5 w-5 text-gray-300" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      case 'running':
        return 'bg-blue-500'
      default:
        return 'bg-gray-300'
    }
  }

  const getTextColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700'
      case 'failed':
        return 'text-red-700'
      case 'running':
        return 'text-blue-700'
      default:
        return 'text-gray-500'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Execution Timeline</h3>
        <div className="flex items-center space-x-4 text-sm">
          <span className={`font-medium ${
            summary.status === 'completed' ? 'text-green-600' :
            summary.status === 'failed' ? 'text-red-600' :
            summary.status === 'running' ? 'text-blue-600' :
            'text-gray-600'
          }`}>
            Status: {summary.status}
          </span>
          {summary.duration_seconds && (
            <span className="text-gray-500">
              Duration: {formatDistanceStrict(0, summary.duration_seconds * 1000)}
            </span>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-8 top-8 bottom-0 w-0.5 bg-gray-200"></div>
        
        <div className="space-y-6">
          {steps.map((step, idx) => {
            const Icon = step.icon
            const isLast = idx === steps.length - 1
            
            return (
              <div key={step.name} className="relative flex items-start">
                {/* Connector Line */}
                {!isLast && (
                  <div className={`absolute left-8 top-8 bottom-0 w-0.5 ${
                    step.status === 'completed' ? 'bg-green-500' : 'bg-gray-200'
                  }`}></div>
                )}
                
                {/* Icon Circle */}
                <div className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-full border-4 border-white ${
                  getStatusColor(step.status)
                }`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                
                {/* Content */}
                <div className="ml-4 flex-1">
                  <div className="flex items-center space-x-3 mb-1">
                    <h4 className={`font-semibold ${getTextColor(step.status)}`}>
                      {step.name}
                    </h4>
                    {getStatusIcon(step.status)}
                    {step.count > 0 && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">
                        {step.count} items
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{step.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Metadata */}
      {summary.metadata && Object.keys(summary.metadata).length > 0 && (
        <div className="mt-6 pt-6 border-t">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Execution Details</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-gray-500">Workflow ID:</span>
              <div className="font-mono text-gray-700 truncate">
                {summary.metadata.workflow_id}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Agent ID:</span>
              <div className="font-mono text-gray-700 truncate">
                {summary.metadata.agent_id}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Workflow Type:</span>
              <div className="font-medium text-gray-700">
                {summary.workflow_type}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Initiative:</span>
              <div className="font-mono text-gray-700 truncate">
                {summary.initiative_id.slice(0, 8)}...
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}