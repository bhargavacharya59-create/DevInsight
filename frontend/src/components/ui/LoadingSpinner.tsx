import clsx from 'clsx';

export default function LoadingSpinner({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  return (
    <div className={clsx('flex items-center justify-center', className)}>
      <div className={clsx(
        'rounded-full border-2 border-slate-700 border-t-brand-500 animate-spin',
        size === 'sm' && 'w-4 h-4',
        size === 'md' && 'w-8 h-8',
        size === 'lg' && 'w-12 h-12',
      )} />
    </div>
  );
}
