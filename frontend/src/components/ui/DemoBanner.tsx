import { FlaskConical, X } from 'lucide-react';
import { useState } from 'react';

export default function DemoBanner() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-purple-900/30 border-b border-purple-700/30 text-sm">
      <FlaskConical size={14} className="text-purple-400 shrink-0" />
      <span className="text-purple-300">
        <strong>Demo Mode</strong> — All telemetry is synthetic and clearly labeled. No real ShopSphere infrastructure is connected.
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="ml-auto text-purple-400 hover:text-purple-200 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}
