'use client'

import { useState } from 'react'
import { Play, Maximize2, X } from 'lucide-react'

interface MediaViewerProps {
  url: string
  type: 'image' | 'video' | 'reel' | 'carousel' | string
  className?: string
  showControls?: boolean
}

export default function MediaViewer({ 
  url, 
  type, 
  className = '',
  showControls = true 
}: MediaViewerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState(false)

  const isVideo = type === 'video' || type === 'reel'

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 ${className}`}>
        <div className="text-center text-gray-500 p-4">
          <p className="text-sm">Failed to load media</p>
          <p className="text-xs mt-1">URL: {url.slice(0, 50)}...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className={`relative group ${className}`}>
        {isVideo ? (
          <div className="relative w-full h-full">
            <video
              src={url}
              className="w-full h-full object-cover"
              controls={showControls}
              onError={() => setError(true)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            {!isPlaying && (
              <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
                <Play className="h-12 w-12 text-white" />
              </div>
            )}
          </div>
        ) : (
          <img
            src={url}
            alt="Generated content"
            className="w-full h-full object-cover"
            onError={() => setError(true)}
          />
        )}

        {/* Fullscreen button */}
        {showControls && (
          <button
            onClick={() => setIsFullscreen(true)}
            className="absolute top-2 right-2 p-1.5 bg-black bg-opacity-50 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4">
          <button
            onClick={() => setIsFullscreen(false)}
            className="absolute top-4 right-4 p-2 bg-white bg-opacity-20 rounded-lg text-white hover:bg-opacity-30 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
          
          <div className="max-w-7xl max-h-full">
            {isVideo ? (
              <video
                src={url}
                className="max-w-full max-h-full"
                controls
                autoPlay
              />
            ) : (
              <img
                src={url}
                alt="Generated content"
                className="max-w-full max-h-full"
              />
            )}
          </div>
        </div>
      )}
    </>
  )
}