import React from 'react';
import { AlertCircle, CheckCircle, Info, XCircle, X } from 'lucide-react';

export function Alert({ type = 'info', title, message, onClose, className = '' }) {
  const styles = {
    info: {
      container: 'bg-[#F0F9FF] border-[#BAE6FD] text-[#0C4A6E]',
      icon: <Info className="w-5 h-5 text-[#0369A1] flex-shrink-0 mt-0.5" />,
    },
    success: {
      container: 'bg-[#E8FBF5] border-[#A3F3DC] text-[#0B5B44]',
      icon: <CheckCircle className="w-5 h-5 text-[#00D294] flex-shrink-0 mt-0.5" />,
    },
    warning: {
      container: 'bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]',
      icon: <AlertCircle className="w-5 h-5 text-[#D97706] flex-shrink-0 mt-0.5" />,
    },
    error: {
      container: 'bg-[#FFF1F2] border-[#FECDD3] text-[#9F1239]',
      icon: <XCircle className="w-5 h-5 text-[#E11D48] flex-shrink-0 mt-0.5" />,
    },
  }[type] || styles.info;

  return (
    <div className={`flex items-start gap-3.5 p-4 rounded-xl border text-xs shadow-subtle animate-in fade-in duration-150 ${styles.container} ${className}`}>
      {styles.icon}
      <div className="flex-1 min-w-0">
        {title && <h5 className="font-bold text-xs mb-0.5 tracking-tight">{title}</h5>}
        <div className="text-xs leading-relaxed opacity-95">{message}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-current opacity-60 hover:opacity-100 p-1 rounded-lg hover:bg-black/5 transition-colors"
          title="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
