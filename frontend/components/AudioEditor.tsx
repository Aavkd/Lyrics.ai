'use client';

/**
 * Flow-to-Lyrics: Audio Editor Component
 * ======================================
 * Professional workspace with waveform visualization, region mapping,
 * and segment data table.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
    Play,
    Pause,
    ZoomIn,
    ZoomOut,
    Upload,
    Music,
    Loader2,
    AlertCircle,
    RotateCcw
} from 'lucide-react';
import { useAudioStore, Segment } from '@/store/useAudioStore';
import { uploadAudio } from '@/lib/api';
import SegmentList from './SegmentList';

// Wavesurfer types
import type WaveSurfer from 'wavesurfer.js';
import type RegionsPlugin from 'wavesurfer.js/dist/plugins/regions';

// =============================================================================
// COMPONENT
// =============================================================================

export default function AudioEditor() {
    const waveformRef = useRef<HTMLDivElement>(null);
    const wavesurferRef = useRef<WaveSurfer | null>(null);
    const regionsRef = useRef<RegionsPlugin | null>(null);

    const [isDragging, setIsDragging] = useState(false);

    const {
        file,
        analysisData,
        isPlaying,
        currentTime,
        zoomLevel,
        isLoading,
        error,
        activeSegmentId,
        hoveredSegmentId,
        setFile,
        setAnalysisData,
        setSegments,
        setIsPlaying,
        setCurrentTime,
        setZoomLevel,
        setLoading,
        setError,
        setActiveSegmentId,
        reset,
    } = useAudioStore();

    // ===========================================================================
    // WAVESURFER INITIALIZATION (Original working version)
    // ===========================================================================

    useEffect(() => {
        if (!waveformRef.current || !file) return;

        let ws: WaveSurfer | null = null;

        const initWavesurfer = async () => {
            // Dynamic import to avoid SSR issues
            const WaveSurferModule = (await import('wavesurfer.js')).default;
            const RegionsPluginModule = (await import('wavesurfer.js/dist/plugins/regions')).default;

            // Create regions plugin
            const regions = RegionsPluginModule.create();
            regionsRef.current = regions;

            // Create wavesurfer instance (original working config)
            ws = WaveSurferModule.create({
                container: waveformRef.current!,
                waveColor: '#6366f1',
                progressColor: '#a855f7',
                cursorColor: '#f472b6',
                cursorWidth: 2,
                height: 180,
                barWidth: 2,
                barGap: 1,
                barRadius: 2,
                normalize: true,
                plugins: [regions],
            });

            wavesurferRef.current = ws;

            // Load audio from File
            const url = URL.createObjectURL(file);
            ws.load(url);

            // Event listeners
            ws.on('ready', () => {
                // Apply initial zoom
                ws?.zoom(zoomLevel);
                // NOTE: Regions are rendered by the analysisData sync useEffect below
            });

            ws.on('play', () => setIsPlaying(true));
            ws.on('pause', () => setIsPlaying(false));
            ws.on('timeupdate', (time) => {
                setCurrentTime(time);
                // Update active segment
                const segments = analysisData?.blocks?.[0]?.segments;
                if (segments) {
                    for (let i = 0; i < segments.length; i++) {
                        const seg = segments[i];
                        if (time >= seg.time_start && time < seg.time_start + seg.duration) {
                            setActiveSegmentId(`segment-${i}`);
                            return;
                        }
                    }
                    setActiveSegmentId(null);
                }
            });
            ws.on('finish', () => {
                setIsPlaying(false);
                setActiveSegmentId(null);
            });
        };

        initWavesurfer();

        return () => {
            ws?.destroy();
            wavesurferRef.current = null;
            regionsRef.current = null;
        };
    }, [file]); // eslint-disable-line react-hooks/exhaustive-deps

    // ===========================================================================
    // ZOOM SYNC
    // ===========================================================================

    useEffect(() => {
        if (wavesurferRef.current) {
            wavesurferRef.current.zoom(zoomLevel);
        }
    }, [zoomLevel]);

    // ===========================================================================
    // KEYBOARD CONTROLS
    // ===========================================================================

    useEffect(() => {
        if (!file) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.code === 'Space' && !e.repeat) {
                e.preventDefault();
                if (wavesurferRef.current) {
                    wavesurferRef.current.playPause();
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [file]);

    // ===========================================================================
    // PLAY/PAUSE SYNC
    // ===========================================================================

    useEffect(() => {
        if (!wavesurferRef.current) return;

        if (isPlaying) {
            wavesurferRef.current.play();
        } else {
            wavesurferRef.current.pause();
        }
    }, [isPlaying]);

    // ===========================================================================
    // REGION RENDERING
    // ===========================================================================

    const renderRegions = useCallback((segments: Segment[]) => {
        if (!regionsRef.current) return;

        // Clear existing regions
        regionsRef.current.clearRegions();

        // Create regions from segments
        segments.forEach((segment, index) => {
            regionsRef.current?.addRegion({
                id: `segment-${index}`,
                start: segment.time_start,
                end: segment.time_start + segment.duration,
                color: segment.is_stressed
                    ? 'rgba(168, 85, 247, 0.4)'   // Purple for stressed
                    : 'rgba(99, 102, 241, 0.3)',  // Indigo for normal
                drag: true,
                resize: true,
            });
        });
    }, []);

    // ===========================================================================
    // ANALYSIS DATA SYNC
    // ===========================================================================

    useEffect(() => {
        if (analysisData?.blocks?.[0]?.segments && regionsRef.current && wavesurferRef.current) {
            renderRegions(analysisData.blocks[0].segments);
        }
    }, [analysisData, renderRegions]);

    // ===========================================================================
    // ACTIVE/HOVERED REGION HIGHLIGHTING
    // ===========================================================================

    useEffect(() => {
        if (!regionsRef.current) return;

        const regions = regionsRef.current.getRegions();
        regions.forEach((region) => {
            const element = region.element;
            if (!element) return;

            const isActive = region.id === activeSegmentId;
            const isHovered = region.id === hoveredSegmentId;

            if (isActive) {
                element.style.backgroundColor = 'rgba(236, 72, 153, 0.5)';
                element.style.border = '2px solid #ec4899';
            } else if (isHovered) {
                element.style.backgroundColor = 'rgba(129, 140, 248, 0.5)';
                element.style.border = '2px solid #818cf8';
            } else {
                const isStressed = region.id && analysisData?.blocks?.[0]?.segments.some(
                    (s, i) => `segment-${i}` === region.id && s.is_stressed
                );
                element.style.backgroundColor = isStressed
                    ? 'rgba(168, 85, 247, 0.4)'
                    : 'rgba(99, 102, 241, 0.3)';
                element.style.border = 'none';
            }
        });
    }, [activeSegmentId, hoveredSegmentId, analysisData]);

    // ===========================================================================
    // REGION UPDATE HANDLER
    // ===========================================================================

    const handleRegionUpdate = useCallback(() => {
        if (!regionsRef.current || !analysisData) return;

        const regions = regionsRef.current.getRegions();
        const updatedSegments: Segment[] = Object.values(regions).map((region) => ({
            time_start: region.start,
            duration: region.end - region.start,
            is_stressed: analysisData.blocks[0]?.segments.find(
                (s) => Math.abs(s.time_start - region.start) < 0.01
            )?.is_stressed ?? false,
        }));

        updatedSegments.sort((a, b) => a.time_start - b.time_start);
        setSegments(updatedSegments);
    }, [analysisData, setSegments]);

    useEffect(() => {
        if (!regionsRef.current) return;

        const regions = regionsRef.current;
        regions.on('region-updated', handleRegionUpdate);

        return () => {
            regions.un('region-updated', handleRegionUpdate);
        };
    }, [handleRegionUpdate]);

    // ===========================================================================
    // FILE UPLOAD HANDLERS
    // ===========================================================================

    const handleDrop = useCallback(
        async (e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            setIsDragging(false);

            const droppedFile = e.dataTransfer.files[0];
            if (!droppedFile) return;

            await processFile(droppedFile);
        },
        [] // eslint-disable-line react-hooks/exhaustive-deps
    );

    const handleFileSelect = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const selectedFile = e.target.files?.[0];
            if (!selectedFile) return;

            await processFile(selectedFile);
        },
        [] // eslint-disable-line react-hooks/exhaustive-deps
    );

    const processFile = async (uploadedFile: File) => {
        reset();
        setFile(uploadedFile);
        setLoading(true);
        setError(null);

        try {
            const data = await uploadAudio(uploadedFile);
            setAnalysisData(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setLoading(false);
        }
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    // ===========================================================================
    // TRANSPORT CONTROLS
    // ===========================================================================

    const handlePlayPause = () => {
        if (!wavesurferRef.current) return;
        wavesurferRef.current.playPause();
    };

    const handleSeek = useCallback((time: number) => {
        if (!wavesurferRef.current) return;
        wavesurferRef.current.setTime(time);
    }, []);

    const handleReset = () => {
        reset();
    };

    // ===========================================================================
    // FORMAT HELPERS
    // ===========================================================================

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // ===========================================================================
    // RENDER
    // ===========================================================================

    return (
        <div className="flex flex-col gap-4 w-full h-full p-4">
            {/* Upload Area (shown when no file) */}
            {!file && (
                <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`
                        relative flex flex-col items-center justify-center 
                        w-full h-64 rounded-2xl border-2 border-dashed 
                        transition-all duration-300 cursor-pointer
                        ${isDragging
                            ? 'border-purple-500 bg-purple-500/10 scale-[1.02]'
                            : 'border-gray-600 bg-gray-800/50 hover:border-purple-400 hover:bg-gray-800'
                        }
                    `}
                >
                    <input
                        type="file"
                        accept=".mp3,.wav,.m4a,.flac,.ogg"
                        onChange={handleFileSelect}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <Upload className={`w-12 h-12 mb-4 ${isDragging ? 'text-purple-400' : 'text-gray-400'}`} />
                    <p className="text-lg font-medium text-gray-200">
                        {isDragging ? 'Release to upload' : 'Drag & drop your audio file'}
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                        or click to select • MP3, WAV, M4A, FLAC, OGG
                    </p>
                    <p className="text-xs text-gray-600 mt-4">
                        Press <kbd className="px-2 py-1 rounded bg-gray-700 text-gray-300">Space</kbd> to play/pause
                    </p>
                </div>
            )}

            {/* Loading State */}
            {isLoading && (
                <div className="flex flex-col items-center justify-center h-64 rounded-2xl bg-gray-800/50 border border-gray-700">
                    <Loader2 className="w-12 h-12 text-purple-500 animate-spin mb-4" />
                    <p className="text-gray-300">Analyzing audio...</p>
                    <p className="text-sm text-gray-500 mt-1">Detecting syllables and rhythm</p>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <p className="text-red-300">{error}</p>
                </div>
            )}

            {/* Waveform Editor (shown when file is loaded) */}
            {file && !isLoading && (
                <>
                    {/* File Info Bar */}
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-800/80 border border-gray-700">
                        <Music className="w-5 h-5 text-purple-400" />
                        <span className="text-gray-200 font-medium truncate">{file.name}</span>
                        {analysisData && (
                            <>
                                <span className="text-gray-500">•</span>
                                <span className="text-gray-400 text-sm">
                                    {analysisData.meta.tempo.toFixed(1)} BPM
                                </span>
                                <span className="text-gray-500">•</span>
                                <span className="text-gray-400 text-sm">
                                    {analysisData.blocks[0]?.segments.length || 0} segments
                                </span>
                            </>
                        )}
                        <button
                            onClick={handleReset}
                            className="ml-auto p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
                            title="Upload new file"
                        >
                            <RotateCcw className="w-4 h-4 text-gray-300" />
                        </button>
                    </div>

                    {/* Waveform Container */}
                    <div className="relative p-4 rounded-2xl bg-gray-800/80 border border-gray-700">
                        <div
                            ref={waveformRef}
                            className="w-full rounded-lg overflow-hidden"
                        />
                    </div>

                    {/* Transport Controls */}
                    <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-gray-800/80 border border-gray-700">
                        {/* Time Display */}
                        <div className="flex items-center gap-2">
                            <span className="font-mono text-lg text-gray-200">
                                {formatTime(currentTime)}
                            </span>
                            <span className="text-gray-500">/</span>
                            <span className="font-mono text-gray-400">
                                {analysisData ? formatTime(analysisData.meta.duration) : '0:00'}
                            </span>
                        </div>

                        {/* Play/Pause */}
                        <button
                            onClick={handlePlayPause}
                            className="flex items-center justify-center w-14 h-14 rounded-full bg-purple-600 hover:bg-purple-500 transition-colors shadow-lg shadow-purple-500/20"
                        >
                            {isPlaying ? (
                                <Pause className="w-6 h-6 text-white" />
                            ) : (
                                <Play className="w-6 h-6 text-white ml-1" />
                            )}
                        </button>

                        {/* Zoom Controls */}
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setZoomLevel(Math.max(10, zoomLevel - 10))}
                                className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
                                title="Zoom Out"
                            >
                                <ZoomOut className="w-5 h-5 text-gray-300" />
                            </button>
                            <input
                                type="range"
                                min="10"
                                max="200"
                                value={zoomLevel}
                                onChange={(e) => setZoomLevel(Number(e.target.value))}
                                className="w-24 h-2 appearance-none bg-gray-600 rounded-full cursor-pointer
                                    [&::-webkit-slider-thumb]:appearance-none
                                    [&::-webkit-slider-thumb]:w-4
                                    [&::-webkit-slider-thumb]:h-4
                                    [&::-webkit-slider-thumb]:bg-purple-500
                                    [&::-webkit-slider-thumb]:rounded-full
                                    [&::-webkit-slider-thumb]:cursor-pointer
                                "
                            />
                            <button
                                onClick={() => setZoomLevel(Math.min(200, zoomLevel + 10))}
                                className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
                                title="Zoom In"
                            >
                                <ZoomIn className="w-5 h-5 text-gray-300" />
                            </button>
                        </div>
                    </div>

                    {/* Segment Table */}
                    <div className="h-[350px] rounded-xl bg-gray-800/80 border border-gray-700">
                        <SegmentList onSeek={handleSeek} />
                    </div>
                </>
            )}
        </div>
    );
}
