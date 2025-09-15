'use client'

import { Research } from '@/lib/types'
import { FileSearch, ExternalLink, Hash, TrendingUp, Lightbulb, Link } from 'lucide-react'
import { format } from 'date-fns'

interface ResearchDisplayProps {
  research: Research[]
}

export default function ResearchDisplay({ research }: ResearchDisplayProps) {
  if (research.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <div className="text-center text-gray-500">
          <FileSearch className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-lg font-medium">No Research Data</p>
          <p className="text-sm mt-1">No research was conducted in this execution</p>
        </div>
      </div>
    )
  }

  const entry = research[0] // Usually one comprehensive research entry per execution
  const rawData = entry.raw_data || {}
  const insights = entry.insights || []
  const hashtags = rawData.recommended_hashtags || []
  const opportunities = rawData.content_opportunities || []
  const sources = entry.sources || []

  return (
    <div className="space-y-6">
      {/* Summary Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center space-x-2 mb-4">
          <FileSearch className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Research Summary</h3>
        </div>
        
        {entry.summary && (
          <div className="prose prose-sm max-w-none text-gray-700">
            <p>{entry.summary}</p>
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{insights.length}</div>
            <div className="text-xs text-gray-500">Key Findings</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{sources.length}</div>
            <div className="text-xs text-gray-500">Sources</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{hashtags.length}</div>
            <div className="text-xs text-gray-500">Hashtags</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{opportunities.length}</div>
            <div className="text-xs text-gray-500">Opportunities</div>
          </div>
        </div>
      </div>

      {/* Key Findings */}
      {insights.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-900">Key Findings</h3>
          </div>
          <div className="space-y-3">
            {insights.map((insight, idx) => (
              <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  {insight.topic || `Finding ${idx + 1}`}
                </div>
                <p className="text-sm text-gray-700">
                  {insight.finding}
                </p>
                {insight.source && (
                  <a
                    href={insight.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 mt-2"
                  >
                    <Link className="h-3 w-3" />
                    <span>Source</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {insight.relevance_score && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-500">Relevance:</span>
                      <div className="flex-1 max-w-xs bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${(insight.relevance_score * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-600">
                        {(insight.relevance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Content Opportunities */}
      {opportunities.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Lightbulb className="h-5 w-5 text-yellow-600" />
            <h3 className="text-lg font-semibold text-gray-900">Content Opportunities</h3>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {opportunities.map((opp: any, idx: number) => (
              <div key={idx} className="p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border border-yellow-200">
                <div className="flex items-start space-x-3">
                  <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${
                    opp.priority === 'high' ? 'bg-red-500' :
                    opp.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`} />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 capitalize">
                      {opp.type || 'Opportunity'}
                    </div>
                    <p className="text-sm text-gray-700 mt-1">
                      {opp.description}
                    </p>
                    {opp.priority && (
                      <span className={`inline-block mt-2 px-2 py-1 rounded-full text-xs font-medium ${
                        opp.priority === 'high' ? 'bg-red-100 text-red-700' :
                        opp.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 
                        'bg-green-100 text-green-700'
                      }`}>
                        {opp.priority} priority
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Hashtags */}
      {hashtags.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Hash className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">Recommended Hashtags</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {hashtags.map((tag: string, idx: number) => (
              <span
                key={idx}
                className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200"
              >
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Link className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Research Sources</h3>
          </div>
          <div className="space-y-2">
            {sources.map((source, idx) => (
              <a
                key={idx}
                href={source}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700 p-2 hover:bg-gray-50 rounded"
              >
                <ExternalLink className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">{source}</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}