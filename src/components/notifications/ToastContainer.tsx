/**
 * ToastContainer.tsx
 * Portal-rendered fixed stack, top-right of the screen.
 * Renders up to MAX_TOASTS toasts with AnimatePresence.
 * Also exposes a sound toggle button.
 */

import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Volume2, VolumeX } from 'lucide-react';
import { useToast } from '../../hooks/useToast';
import ToastNotification from './ToastNotification';

interface ToastContainerProps {
  /** Called when user clicks a toast body to navigate to a job */
  onNavigate?: (jobId: string | number) => void;
}

export default function ToastContainer({ onNavigate }: ToastContainerProps) {
  const { toasts, dismissToast, pauseToast, resumeToast, soundEnabled, setSoundEnabled } =
    useToast();

  const container = (
    <div
      aria-label="Notifications"
      role="region"
      className="pointer-events-none fixed right-5 top-5 z-[9999] flex flex-col items-end gap-3"
      style={{ maxWidth: '360px', width: '100%' }}
    >
      {/* Sound toggle — always visible when there are toasts */}
      <AnimatePresence>
        {toasts.length > 0 && (
          <motion.button
            key="sound-toggle"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            type="button"
            onClick={() => setSoundEnabled(!soundEnabled)}
            aria-label={soundEnabled ? 'Mute toast sounds' : 'Enable toast sounds'}
            title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
            className="pointer-events-auto flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-md border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Toast stack */}
      <AnimatePresence initial={false} mode="popLayout">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto w-full">
            <ToastNotification
              toast={toast}
              onDismiss={dismissToast}
              onPause={pauseToast}
              onResume={resumeToast}
              onNavigate={onNavigate}
            />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );

  // Render via portal so it floats above all page content
  return createPortal(container, document.body);
}
