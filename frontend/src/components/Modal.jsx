import { useEffect } from 'react';

/**
 * Reusable Modal Component
 * 
 * A flexible modal dialog that can be used across all features in the application.
 * Includes backdrop blur, animations, keyboard shortcuts (ESC to close), and 
 * prevents body scroll when open.
 * 
 * @example
 * ```jsx
 * import Modal from './Modal';
 * 
 * function MyComponent() {
 *   const [showModal, setShowModal] = useState(false);
 *   
 *   return (
 *     <>
 *       <button onClick={() => setShowModal(true)}>Open Modal</button>
 *       
 *       <Modal
 *         isOpen={showModal}
 *         onClose={() => setShowModal(false)}
 *         title="My Modal Title"
 *         icon={<MyIcon />}
 *         maxWidth="max-w-lg"
 *         footer={
 *           <button onClick={() => setShowModal(false)}>Close</button>
 *         }
 *       >
 *         <p>Modal content goes here</p>
 *       </Modal>
 *     </>
 *   );
 * }
 * ```
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Controls modal visibility
 * @param {Function} props.onClose - Callback when modal should close (ESC key or backdrop click)
 * @param {string} props.title - Modal title displayed in header
 * @param {React.ReactNode} props.children - Modal body content
 * @param {string} [props.maxWidth='max-w-xl'] - Tailwind max-width class (e.g., 'max-w-sm', 'max-w-2xl')
 * @param {boolean} [props.showClose=true] - Show close button in header
 * @param {React.ReactNode} [props.footer] - Optional footer content (renders below body)
 * @param {React.ReactNode} [props.icon] - Optional icon displayed next to title
 */
export default function Modal({ 
    isOpen, 
    onClose, 
    title, 
    children, 
    maxWidth = 'max-w-xl',
    showClose = true,
    footer = null,
    icon = null 
}) {
    // Close on Escape key
    useEffect(() => {
        if (!isOpen) return;
        
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                onClose?.();
            }
        };
        
        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    // Prevent body scroll when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="modal-backdrop animate-fade-in" onClick={onClose}>
            <div 
                className={`modal ${maxWidth} w-full mx-4 animate-scale-in`}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="modal-header">
                    <div className="flex items-center gap-3">
                        {icon && <div className="text-accent">{icon}</div>}
                        <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
                    </div>
                    {showClose && (
                        <button
                            className="btn-icon-sm"
                            onClick={onClose}
                            type="button"
                        >
                            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    )}
                </div>

                {/* Body */}
                <div className="modal-body">
                    {children}
                </div>

                {/* Footer (optional) */}
                {footer && (
                    <div className="modal-footer">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}
