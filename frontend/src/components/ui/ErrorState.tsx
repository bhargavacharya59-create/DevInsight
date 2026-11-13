import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({ message = 'Failed to load data', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="w-12 h-12 bg-red-900/30 rounded-full flex items-center justify-center">
        <AlertCircle size={24} className="text-red-400" />
      </div>
      <div className="text-center">
        <p className="text-slate-300 font-medium">{message}</p>
        <p className="text-slate-500 text-sm mt-1">Check the backend connection and try again.</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}
