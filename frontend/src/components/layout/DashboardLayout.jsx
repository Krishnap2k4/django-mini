import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-surface-alt">
      <Sidebar />
      <div className="ml-[260px] flex flex-col min-h-screen">
        <Outlet />
      </div>
    </div>
  );
}
