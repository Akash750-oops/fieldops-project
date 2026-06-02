export interface JobNotificationDetail {
  id: string | number;
  title: string;
  description: string;
  location: string;
  priority: string;
  customer_name: string;
  customer_phone: string;
  estimated_value: number;
  sla_deadline: string;
  distance_km: number;
  required_skills: string[];
}

export interface TechnicianNotification {
  id: string;
  type: 'JOB_ASSIGNED' | 'SLA_WARNING' | 'JOB_UPDATED' | 'SYSTEM';
  title: string;
  message: string;
  isRead: boolean;
  createdAt: string;
  jobId?: string | number;
  job?: JobNotificationDetail;
}

export interface NotificationBellProps {
  unreadCount: number;
  onClick: () => void;
  isAnimated?: boolean;
  showSound?: boolean;
  className?: string;
}

export interface NotificationDetailProps {
  notification: TechnicianNotification;
  job?: JobNotificationDetail;
  loading?: boolean;
  error?: string;
  onAccept: (jobId: string | number) => void;
  onReject: (jobId: string | number, reason: string) => void;
  onReassign: (jobId: string | number) => void;
  onClose: () => void;
  socket?: any;
}

export interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: TechnicianNotification[];
  onNotificationClick: (notification: TechnicianNotification) => void;
  onMarkAllAsRead?: () => void;
  loading?: boolean;
}

export interface PermissionRequestProps {
  onPermissionChange?: (status: string) => void;
  className?: string;
  compact?: boolean;
}
