'use client'

import { Post, MediaFile } from '@/lib/types'
import { format } from 'date-fns'
import { 
  Image, 
  Video, 
  Link, 
  Calendar, 
  Hash, 
  ExternalLink,
  Facebook,
  Instagram,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  PenTool
} from 'lucide-react'
import MediaViewer from './MediaViewer'

interface ContentDisplayProps {
  posts: Post[]
  mediaFiles: MediaFile[]
}

export default function ContentDisplay({ posts, mediaFiles }: ContentDisplayProps) {
  // Group media files by post
  const getMediaForPost = (postId: string) => {
    // In a real scenario, you'd have a direct relationship
    // For now, we'll match by execution_id and timing
    return mediaFiles.filter(media => 
      media.execution_step === 'Content Creation'
    )
  }

  const getPostStatusColor = (status?: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-800'
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'draft':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getPostTypeIcon = (type: string) => {
    switch (type) {
      case 'video':
      case 'reel':
        return <Video className="h-5 w-5" />
      case 'carousel':
        return <Image className="h-5 w-5" />
      default:
        return <Image className="h-5 w-5" />
    }
  }

  if (posts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <div className="text-center text-gray-500">
          <PenTool className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-lg font-medium">No Content Generated</p>
          <p className="text-sm mt-1">No posts were created in this execution</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Content Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{posts.length}</div>
            <div className="text-sm text-gray-500">Total Posts</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {posts.filter(p => p.is_published).length}
            </div>
            <div className="text-sm text-gray-500">Published</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {posts.filter(p => p.status === 'scheduled').length}
            </div>
            <div className="text-sm text-gray-500">Scheduled</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{mediaFiles.length}</div>
            <div className="text-sm text-gray-500">Media Files</div>
          </div>
        </div>
      </div>

      {/* Posts Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {posts.map((post) => (
          <div key={post.id} className="bg-white rounded-lg shadow-sm border overflow-hidden">
            {/* Post Header */}
            <div className="p-4 border-b bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getPostTypeIcon(post.post_type)}
                  <span className="font-medium text-gray-900 capitalize">
                    {post.post_type}
                  </span>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPostStatusColor(post.status)}`}>
                  {post.status || 'draft'}
                </span>
              </div>
              
              {/* Platform Links */}
              <div className="flex items-center space-x-3 text-sm">
                {post.facebook_post_id && (
                  <a
                    href={`https://facebook.com/${post.facebook_post_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center space-x-1 text-blue-600 hover:text-blue-700"
                  >
                    <Facebook className="h-4 w-4" />
                    <span>View</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {post.instagram_post_id && (
                  <a
                    href={`https://instagram.com/p/${post.instagram_post_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center space-x-1 text-pink-600 hover:text-pink-700"
                  >
                    <Instagram className="h-4 w-4" />
                    <span>View</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>

            {/* Media Preview */}
            {post.media_urls && post.media_urls.length > 0 && (
              <div className="relative h-48 bg-gray-100">
                <MediaViewer
                  url={post.media_urls[0]}
                  type={post.post_type === 'video' || post.post_type === 'reel' ? 'video' : 'image'}
                  className="w-full h-full object-cover"
                />
                {post.media_urls.length > 1 && (
                  <div className="absolute top-2 right-2 bg-black bg-opacity-60 text-white px-2 py-1 rounded text-xs">
                    +{post.media_urls.length - 1} more
                  </div>
                )}
              </div>
            )}

            {/* Content */}
            <div className="p-4 space-y-3">
              {/* Text Content */}
              {post.text_content && (
                <div className="text-sm text-gray-700 line-clamp-3">
                  {post.text_content}
                </div>
              )}

              {/* Hashtags */}
              {post.hashtags && post.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {post.hashtags.slice(0, 5).map((tag, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700"
                    >
                      <Hash className="h-3 w-3 mr-1" />
                      {tag.replace('#', '')}
                    </span>
                  ))}
                  {post.hashtags.length > 5 && (
                    <span className="text-xs text-gray-500">
                      +{post.hashtags.length - 5} more
                    </span>
                  )}
                </div>
              )}

              {/* Links */}
              {post.links && post.links.length > 0 && (
                <div className="space-y-1">
                  {post.links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 truncate"
                    >
                      <Link className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{link}</span>
                    </a>
                  ))}
                </div>
              )}

              {/* Scheduling */}
              {post.scheduled_time && (
                <div className="flex items-center space-x-1 text-xs text-gray-500">
                  <Calendar className="h-3 w-3" />
                  <span>Scheduled: {format(new Date(post.scheduled_time), 'PPp')}</span>
                </div>
              )}

              {/* Metrics (if published) */}
              {post.is_published && (
                <div className="pt-3 border-t flex items-center justify-between text-xs text-gray-500">
                  <div className="flex items-center space-x-3">
                    <span className="flex items-center space-x-1">
                      <Eye className="h-3 w-3" />
                      <span>{post.reach || 0}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Heart className="h-3 w-3" />
                      <span>{post.engagement || 0}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <MessageCircle className="h-3 w-3" />
                      <span>{post.comments_count || 0}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Share2 className="h-3 w-3" />
                      <span>{post.shares || 0}</span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Media Files Section */}
      {mediaFiles.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Generated Media Files</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {mediaFiles.map((media) => (
              <div key={media.id} className="group relative">
                <div className="aspect-square rounded-lg overflow-hidden bg-gray-100">
                  <MediaViewer
                    url={media.public_url}
                    type={media.file_type}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                </div>
                <div className="mt-2">
                  <div className="text-xs font-medium text-gray-900 capitalize">
                    {media.file_type}
                  </div>
                  {media.prompt_used && (
                    <div className="text-xs text-gray-500 line-clamp-2 mt-1">
                      {media.prompt_used}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}