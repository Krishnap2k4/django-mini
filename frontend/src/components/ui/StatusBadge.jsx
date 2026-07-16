const statusConfig = {
  DRAFT: { label: 'Draft', bg: 'bg-gray-100', text: 'text-gray-700' },
  SUBMITTED: { label: 'Submitted', bg: 'bg-info/10', text: 'text-info' },
  APPROVED: { label: 'Approved', bg: 'bg-accent/10', text: 'text-accent' },
  REJECTED: { label: 'Rejected', bg: 'bg-danger/10', text: 'text-danger' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || statusConfig.DRAFT;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}
