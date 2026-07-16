export default function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-surface rounded-[12px] shadow-card w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-main">{title}</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-main cursor-pointer">
            <span className="material-icons-round">close</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
