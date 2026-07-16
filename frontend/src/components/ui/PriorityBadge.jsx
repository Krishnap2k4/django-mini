const priorityConfig = {
  LOW: { label: 'Low', bg: 'bg-accent/10', text: 'text-accent' },
  MEDIUM: { label: 'Medium', bg: 'bg-warning/10', text: 'text-warning' },
  HIGH: { label: 'High', bg: 'bg-danger/10', text: 'text-danger' },
};

export default function PriorityBadge({ priority }) {
  const config = priorityConfig[priority] || priorityConfig.MEDIUM;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}
