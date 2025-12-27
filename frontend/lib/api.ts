/**
 * Flow-to-Lyrics: API Client
 * ==========================
 * Handles communication with the FastAPI backend.
 */

import { AnalysisData } from '@/store/useAudioStore';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Upload an audio file and get the Pivot JSON analysis.
 * 
 * @param file - The audio file to upload (MP3, WAV, etc.)
 * @returns The analysis data with segments
 * @throws Error if upload or processing fails
 */
export async function uploadAudio(file: File): Promise<AnalysisData> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = errorData?.detail || `Upload failed: ${response.statusText}`;
        throw new Error(message);
    }

    const data = await response.json();
    return data as AnalysisData;
}

/**
 * Check if the backend is available.
 */
export async function healthCheck(): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
