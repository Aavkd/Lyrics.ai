'use client';

/**
 * Flow-to-Lyrics: Segment List Component
 * =======================================
 * A simple scrollable data table showing segment information.
 */

import { useCallback } from 'react';
import { Clock, Zap } from 'lucide-react';
import { useAudioStore, Segment } from '@/store/useAudioStore';

// =============================================================================
// TYPES
// =============================================================================

interface SegmentListProps {
    onSeek: (time: number) => void;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function SegmentList({ onSeek }: SegmentListProps) {
    const {
        analysisData,
        activeSegmentId,
        hoveredSegmentId,
        setHoveredSegmentId,
    } = useAudioStore();

    const segments = analysisData?.blocks?.[0]?.segments ?? [];

    // ===========================================================================
    // FORMAT HELPERS
    // ===========================================================================

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 100);
        return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
    };

    const formatDuration = (seconds: number): string => {
        const ms = Math.floor(seconds * 1000);
        return `${ms}ms`;
    };

    // ===========================================================================
    // HANDLERS
    // ===========================================================================

    const handleRowClick = useCallback((segment: Segment) => {
        onSeek(segment.time_start);
    }, [onSeek]);

    const handleRowHover = useCallback((index: number | null) => {
        setHoveredSegmentId(index !== null ? `segment-${index}` : null);
    }, [setHoveredSegmentId]);

    // ===========================================================================
    // RENDER
    // ===========================================================================

    if (segments.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-gray-500">
                <p>No segments loaded</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 bg-gray-800/50">
                <h3 className="text-sm font-semibold text-gray-300">Segment Data</h3>
                <span className="text-xs text-gray-500">{segments.length} segments</span>
            </div>

            {/* Table Header */}
            <div className="grid grid-cols-[60px_1fr_100px_80px] gap-2 px-4 py-2 text-xs font-medium text-gray-400 uppercase tracking-wider border-b border-gray-700/50 bg-gray-800/30">
                <div>ID</div>
                <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Start
                </div>
                <div>Duration</div>
                <div className="flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    Stress
                </div>
            </div>

            {/* Scrollable Table Body */}
            <div className="flex-1 overflow-y-auto">
                {segments.map((segment, index) => {
                    const segmentId = `segment-${index}`;
                    const isActive = activeSegmentId === segmentId;
                    const isHovered = hoveredSegmentId === segmentId;

                    return (
                        <div
                            key={segmentId}
                            onClick={() => handleRowClick(segment)}
                            onMouseEnter={() => handleRowHover(index)}
                            onMouseLeave={() => handleRowHover(null)}
                            className={`
                                grid grid-cols-[60px_1fr_100px_80px] gap-2 px-4 py-2.5
                                text-sm cursor-pointer transition-colors duration-150
                                border-b border-gray-800/50
                                ${isActive
                                    ? 'bg-purple-500/20 border-l-2 border-l-purple-500'
                                    : isHovered
                                        ? 'bg-gray-700/50 border-l-2 border-l-indigo-400'
                                        : 'hover:bg-gray-800/50 border-l-2 border-l-transparent'
                                }
                            `}
                        >
                            {/* ID */}
                            <div className="font-mono text-gray-400">
                                {(index + 1).toString().padStart(2, '0')}
                            </div>

                            {/* Start Time */}
                            <div className="font-mono text-gray-200">
                                {formatTime(segment.time_start)}
                            </div>

                            {/* Duration */}
                            <div className="font-mono text-gray-300">
                                {formatDuration(segment.duration)}
                            </div>

                            {/* Stress Indicator */}
                            <div>
                                {segment.is_stressed ? (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                        Strong
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-700/50 text-gray-500">
                                        Weak
                                    </span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Footer with metadata */}
            {analysisData && (
                <div className="flex items-center justify-between px-4 py-2 text-xs text-gray-500 border-t border-gray-700 bg-gray-800/30">
                    <span>BPM: {analysisData.meta.tempo.toFixed(1)}</span>
                    <span>Duration: {formatTime(analysisData.meta.duration)}</span>
                </div>
            )}
        </div>
    );
}
