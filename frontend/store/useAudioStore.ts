/**
 * Flow-to-Lyrics: Audio Store
 * ============================
 * Zustand state management for the Segmentation Editor.
 * Handles file state, analysis data, playback, and zoom.
 */

import { create } from 'zustand';

// =============================================================================
// TYPES
// =============================================================================

export interface Segment {
    time_start: number;
    duration: number;
    is_stressed: boolean;
}

export interface Block {
    id: number;
    syllable_target?: number;
    segments: Segment[];
}

export interface AnalysisMeta {
    tempo: number;
    duration: number;
}

export interface AnalysisData {
    meta: AnalysisMeta;
    blocks: Block[];
    _meta?: {
        filename: string;
        file_size_bytes?: number;
        mock_mode?: boolean;
    };
}

// =============================================================================
// STORE INTERFACE
// =============================================================================

interface AudioState {
    // State
    file: File | null;
    analysisData: AnalysisData | null;
    isPlaying: boolean;
    currentTime: number;
    zoomLevel: number;
    isLoading: boolean;
    error: string | null;
    activeSegmentId: string | null;    // Currently playing segment (cursor inside)
    hoveredSegmentId: string | null;   // Row hover in table

    // Actions
    setFile: (file: File | null) => void;
    setAnalysisData: (data: AnalysisData | null) => void;
    setSegments: (segments: Segment[]) => void;
    setIsPlaying: (playing: boolean) => void;
    togglePlay: () => void;
    setCurrentTime: (time: number) => void;
    setZoomLevel: (level: number) => void;
    zoomIn: () => void;
    zoomOut: () => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setActiveSegmentId: (id: string | null) => void;
    setHoveredSegmentId: (id: string | null) => void;
    reset: () => void;
}

// =============================================================================
// STORE IMPLEMENTATION
// =============================================================================

const initialState = {
    file: null,
    analysisData: null,
    isPlaying: false,
    currentTime: 0,
    zoomLevel: 50, // Default zoom level (minPxPerSec)
    isLoading: false,
    error: null,
    activeSegmentId: null,
    hoveredSegmentId: null,
};

export const useAudioStore = create<AudioState>((set, get) => ({
    ...initialState,

    setFile: (file) => set({ file }),

    setAnalysisData: (data) => set({ analysisData: data }),

    setSegments: (segments) => {
        const { analysisData } = get();
        if (!analysisData || !analysisData.blocks.length) return;

        // Update segments in the first block (bi-directional sync with Wavesurfer)
        set({
            analysisData: {
                ...analysisData,
                blocks: [
                    {
                        ...analysisData.blocks[0],
                        segments,
                    },
                    ...analysisData.blocks.slice(1),
                ],
            },
        });
    },

    setIsPlaying: (playing) => set({ isPlaying: playing }),

    togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),

    setCurrentTime: (time) => set({ currentTime: time }),

    setZoomLevel: (level) => set({ zoomLevel: Math.max(10, Math.min(200, level)) }),

    zoomIn: () => set((state) => ({ zoomLevel: Math.min(200, state.zoomLevel + 10) })),

    zoomOut: () => set((state) => ({ zoomLevel: Math.max(10, state.zoomLevel - 10) })),

    setLoading: (loading) => set({ isLoading: loading }),

    setError: (error) => set({ error }),

    setActiveSegmentId: (id) => set({ activeSegmentId: id }),

    setHoveredSegmentId: (id) => set({ hoveredSegmentId: id }),

    reset: () => set(initialState),
}));
