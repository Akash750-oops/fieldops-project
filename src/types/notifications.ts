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

/* ─── Acceptance Timer & Action Components ─────────────────────────── */

export type UrgencyLevel = "safe" | "caution" | "warning" | "critical";
export type ActionState = "IDLE" | "LOADING" | "SUCCESS" | "ERROR" | "TIMEOUT";

export interface CountdownTimerProps {
  expiresAt: string; // ISO 8601
  onExpire: () => void;
  onWarning: () => void;
  jobId: string | number;
  hidden?: boolean;
}

export interface ActionButtonsProps {
  onAccept: (jobId: string | number) => Promise<void>;
  onReject: (jobId: string | number, reason: string) => Promise<void>;
  onReassign: (jobId: string | number, colleagueId?: number) => Promise<void>;
  jobId: string | number;
  disabled?: boolean;
}

export interface WaitingStateProps {
  state: ActionState;
  message?: string;
  onRetry?: () => void;
  onCancel?: () => void;
}

export interface UseCountdownReturn {
  minutes: number;
  seconds: number;
  totalSeconds: number;
  isExpired: boolean;
  urgencyLevel: UrgencyLevel;
}

export interface UseActionStateReturn {
  state: ActionState;
  message: string;
  execute: (actionFn: () => Promise<void>, label?: string) => Promise<void>;
  retry: () => void;
  reset: () => void;
}
