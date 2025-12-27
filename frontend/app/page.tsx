import AudioEditor from '@/components/AudioEditor';
import { Mic2 } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 shadow-lg shadow-purple-500/20">
            <Mic2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Flow-to-Lyrics</h1>
            <p className="text-xs text-gray-400">Segmentation Editor</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
            Phase 2
          </span>
          <span className="text-xs text-gray-500 hidden sm:inline">
            <kbd className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">Space</kbd> Play/Pause
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col w-full max-w-6xl mx-auto">
        <AudioEditor />
      </main>

      {/* Footer */}
      <footer className="flex items-center justify-center px-6 py-4 border-t border-gray-800 text-gray-500 text-sm">
        <p>Upload audio • View detected syllables • Edit segments</p>
      </footer>
    </div>
  );
}
