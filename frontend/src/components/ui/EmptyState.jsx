export default function EmptyState({ icon = 'inbox', message = 'Nothing to show' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-text-muted">
      <span className="material-icons-round text-5xl mb-3">{icon}</span>
      <p className="text-sm">{message}</p>
    </div>
  );
}
