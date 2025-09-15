'use client'

import { Campaign, AdSet } from '@/lib/types'
import { 
  Layout, 
  Target, 
  DollarSign, 
  Calendar, 
  Users, 
  Hash,
  Link,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { format } from 'date-fns'
import { useState } from 'react'

interface PlanDisplayProps {
  campaigns: Campaign[]
  adSets: AdSet[]
}

export default function PlanDisplay({ campaigns, adSets }: PlanDisplayProps) {
  const [expandedCampaigns, setExpandedCampaigns] = useState<Set<string>>(new Set())

  const toggleCampaign = (campaignId: string) => {
    const newExpanded = new Set(expandedCampaigns)
    if (newExpanded.has(campaignId)) {
      newExpanded.delete(campaignId)
    } else {
      newExpanded.add(campaignId)
    }
    setExpandedCampaigns(newExpanded)
  }

  const getAdSetsForCampaign = (campaignId: string) => {
    return adSets.filter(adSet => adSet.campaign_id === campaignId)
  }

  const formatCurrency = (amount?: number) => {
    if (!amount) return '$0'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  if (campaigns.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <div className="text-center text-gray-500">
          <Layout className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-lg font-medium">No Campaign Plan</p>
          <p className="text-sm mt-1">No campaigns were planned in this execution</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Campaign Plan Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{campaigns.length}</div>
            <div className="text-sm text-gray-500">Campaigns</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{adSets.length}</div>
            <div className="text-sm text-gray-500">Ad Sets</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(
                campaigns.reduce((sum, c) => sum + (c.lifetime_budget || 0), 0)
              )}
            </div>
            <div className="text-sm text-gray-500">Total Budget</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(
                campaigns.reduce((sum, c) => sum + (c.daily_budget || 0), 0)
              )}
            </div>
            <div className="text-sm text-gray-500">Daily Budget</div>
          </div>
        </div>
      </div>

      {/* Campaigns */}
      <div className="space-y-4">
        {campaigns.map((campaign) => {
          const campaignAdSets = getAdSetsForCampaign(campaign.id)
          const isExpanded = expandedCampaigns.has(campaign.id)

          return (
            <div key={campaign.id} className="bg-white rounded-lg shadow-sm border overflow-hidden">
              {/* Campaign Header */}
              <div
                className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => toggleCampaign(campaign.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <Layout className="h-5 w-5 text-blue-600" />
                      <h3 className="text-lg font-semibold text-gray-900">{campaign.name}</h3>
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                        {campaign.objective}
                      </span>
                    </div>
                    
                    {campaign.description && (
                      <p className="text-sm text-gray-600 mb-3">{campaign.description}</p>
                    )}

                    <div className="flex flex-wrap gap-4 text-sm">
                      <div className="flex items-center space-x-1">
                        <DollarSign className="h-4 w-4 text-gray-400" />
                        <span className="text-gray-600">
                          {formatCurrency(campaign.lifetime_budget)} lifetime
                        </span>
                      </div>
                      {campaign.daily_budget && (
                        <div className="flex items-center space-x-1">
                          <DollarSign className="h-4 w-4 text-gray-400" />
                          <span className="text-gray-600">
                            {formatCurrency(campaign.daily_budget)}/day
                          </span>
                        </div>
                      )}
                      {campaign.start_date && (
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          <span className="text-gray-600">
                            {format(new Date(campaign.start_date), 'MMM d')} - 
                            {campaign.end_date ? format(new Date(campaign.end_date), 'MMM d, yyyy') : 'Ongoing'}
                          </span>
                        </div>
                      )}
                      <div className="flex items-center space-x-1">
                        <Target className="h-4 w-4 text-gray-400" />
                        <span className="text-gray-600">{campaignAdSets.length} ad sets</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="ml-4 flex-shrink-0">
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </div>
                </div>
              </div>

              {/* Ad Sets (Expanded) */}
              {isExpanded && campaignAdSets.length > 0 && (
                <div className="border-t bg-gray-50 p-6">
                  <h4 className="text-sm font-semibold text-gray-700 mb-4">Ad Sets</h4>
                  <div className="space-y-3">
                    {campaignAdSets.map((adSet) => (
                      <div key={adSet.id} className="bg-white rounded-lg p-4 border">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h5 className="font-medium text-gray-900">{adSet.name}</h5>
                            {adSet.objective && (
                              <span className="text-xs text-gray-500">{adSet.objective}</span>
                            )}
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium text-gray-900">
                              {formatCurrency(adSet.lifetime_budget)}
                            </div>
                            {adSet.daily_budget && (
                              <div className="text-xs text-gray-500">
                                {formatCurrency(adSet.daily_budget)}/day
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Target Audience */}
                        {adSet.target_audience && (
                          <div className="mb-3">
                            <div className="text-xs font-medium text-gray-700 mb-1">Target Audience</div>
                            <div className="flex flex-wrap gap-2 text-xs">
                              {adSet.target_audience.age_range && (
                                <span className="px-2 py-1 bg-gray-100 rounded">
                                  Age: {adSet.target_audience.age_range[0]}-{adSet.target_audience.age_range[1]}
                                </span>
                              )}
                              {adSet.target_audience.locations?.map((loc: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-gray-100 rounded">
                                  {loc}
                                </span>
                              ))}
                              {adSet.target_audience.interests?.slice(0, 3).map((interest: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
                                  {interest}
                                </span>
                              ))}
                              {adSet.target_audience.interests && adSet.target_audience.interests.length > 3 && (
                                <span className="px-2 py-1 text-gray-500">
                                  +{adSet.target_audience.interests.length - 3} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Creative Brief */}
                        {adSet.creative_brief && (
                          <div className="mb-3">
                            <div className="text-xs font-medium text-gray-700 mb-1">Creative Brief</div>
                            <div className="text-xs text-gray-600">
                              <div>Theme: {adSet.creative_brief.theme}</div>
                              <div>Tone: {adSet.creative_brief.tone}</div>
                              {adSet.creative_brief.key_messages && (
                                <div>Messages: {adSet.creative_brief.key_messages.join(', ')}</div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Materials */}
                        {adSet.materials && (
                          <div className="space-y-2">
                            {adSet.materials.hashtags && adSet.materials.hashtags.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {adSet.materials.hashtags.slice(0, 5).map((tag: string, idx: number) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-purple-50 text-purple-700"
                                  >
                                    <Hash className="h-3 w-3 mr-0.5" />
                                    {tag.replace('#', '')}
                                  </span>
                                ))}
                                {adSet.materials.hashtags.length > 5 && (
                                  <span className="text-xs text-gray-500">
                                    +{adSet.materials.hashtags.length - 5} more
                                  </span>
                                )}
                              </div>
                            )}
                            
                            {adSet.materials.links && adSet.materials.links.length > 0 && (
                              <div className="space-y-1">
                                {adSet.materials.links.map((link: string, idx: number) => (
                                  <a
                                    key={idx}
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700"
                                  >
                                    <Link className="h-3 w-3" />
                                    <span className="truncate max-w-xs">{link}</span>
                                  </a>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Post Volume */}
                        <div className="mt-3 pt-3 border-t flex justify-between text-xs text-gray-500">
                          <span>Post Frequency: {adSet.post_frequency || 0}/week</span>
                          <span>Post Volume: {adSet.post_volume || 0} posts</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}