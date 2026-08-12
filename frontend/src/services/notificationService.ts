import { io, Socket } from "socket.io-client";
import api from "./api";
import { TechnicianNotification } from "../types/notifications";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL;

export interface FetchNotificationsResult {
  notifications: TechnicianNotification[];
  unreadCount: number;
  total: number;
}

export const fetchNotifications = async (techId: string | number): Promise<FetchNotificationsResult> => {
  try {
    const response = await api.get(`/technicians/${techId}/notifications`);
    const notifications: TechnicianNotification[] = response.data.notifications.map((n: any) => ({
      id: String(n.id),
      type: n.type,
      title: n.title,
      message: n.body || n.message,
      isRead: n.status === "READ",
      createdAt: n.created_at || n.createdAt,
      jobId: n.job_id,
      job: n.notification_metadata?.job || null
    }));
    return {
      notifications,
      unreadCount: response.data.unread_count,
      total: response.data.total
    };
  } catch (error) {
    console.error("Failed to fetch notifications from backend", error);
    return {
      notifications: [],
      unreadCount: 0,
      total: 0
    };
  }
};

export const fetchUnreadCount = async (techId: string | number): Promise<number> => {
  try {
    const data = await fetchNotifications(techId);
    return data.unreadCount;
  } catch (error) {
    console.error("Failed to fetch unread count", error);
    return 0;
  }
};

export const markNotificationAsRead = async (notificationId: string | number): Promise<any> => {
  try {
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
  } catch (error) {
    console.error("Failed to mark notification as read", error);
    throw error;
  }
};

export const batchMarkAsRead = async (notificationIds: string[]): Promise<any> => {
  try {
    const response = await api.patch("/notifications/batch-read", {
      notification_ids: notificationIds
    });
    return response.data;
  } catch (error) {
    console.error("Failed to batch mark notifications as read", error);
    throw error;
  }
};

export const dismissNotification = async (notificationId: string | number): Promise<any> => {
  try {
    const response = await api.patch(`/notifications/${notificationId}/dismiss`);
    return response.data;
  } catch (error) {
    console.error(`Failed to dismiss notification ${notificationId}`, error);
    throw error;
  }
};

export const cleanupNotifications = async (): Promise<any> => {
  try {
    const response = await api.delete("/notifications/system/cleanup");
    return response.data;
  } catch (error) {
    console.error("Failed to cleanup old notifications", error);
    throw error;
  }
};


export const acceptJob = async (jobId: string | number): Promise<any> => {
  try {
    const response = await api.post(`/jobs/${jobId}/accept`);
    return response.data;
  } catch (error) {
    console.error(`Failed to accept job ${jobId}`, error);
    throw error;
  }
};

export const rejectJob = async (jobId: string | number, reason: string): Promise<any> => {
  try {
    const response = await api.post(`/jobs/${jobId}/reject`, { reason });
    return response.data;
  } catch (error) {
    console.error(`Failed to reject job ${jobId}`, error);
    throw error;
  }
};

export const reassignJob = async (jobId: string | number, colleagueId: string | number, reason: string): Promise<any> => {
  try {
    const response = await api.post(`/jobs/${jobId}/reassign`, {
      new_tech_id: String(colleagueId),
      reason: reason || "Reassigned from notification detail"
    });
    return response.data;
  } catch (error) {
    console.error(`Failed to reassign job ${jobId}`, error);
    throw error;
  }
};

export const registerFCMToken = async (techId: string | number, token: string): Promise<any> => {
  try {
    const response = await api.post(`/technicians/${techId}/fcm-token`, {
      token,
      device_type: "web"
    });
    return response.data;
  } catch (error) {
    console.error("Failed to register FCM token with backend", error);
    throw error;
  }
};

export interface SocketHandlers {
  onConnect?: () => void;
  onDisconnect?: (reason?: string) => void;
  onNewNotification?: (notif: TechnicianNotification) => void;
  onUnreadCount?: (count: number) => void;
  onRead?: (data: any) => void;
}

export const connectNotificationSocket = (tokenOrTechnicianId: string | number, handlers: SocketHandlers = {}): Socket => {
  const techId = tokenOrTechnicianId;
  const socket = io(SOCKET_URL, {
    query: { tech_id: String(techId) },
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 2000,
    transports: ["websocket", "polling"]
  });

  socket.on("connect", () => {
    console.log("Socket connected, room technician:", techId);
    if (handlers.onConnect) handlers.onConnect();
  });

  socket.on("disconnect", (reason: string) => {
    console.log("Socket disconnected:", reason);
    if (handlers.onDisconnect) handlers.onDisconnect(reason);
  });

  const handleNewNotification = (payload: any) => {
    console.log("Real-time notification payload received:", payload);
    const formatted: TechnicianNotification = {
      id: payload.id || `notif-${Date.now()}`,
      type: payload.type || "SYSTEM",
      title: payload.title || "Alert",
      message: payload.body || payload.message || "",
      isRead: false,
      createdAt: payload.created_at || new Date().toISOString(),
      jobId: payload.job_id || payload.jobId,
      job: payload.job || payload.notification_metadata?.job || null
    };

    if (handlers.onNewNotification) {
      handlers.onNewNotification(formatted);
    }
  };

  socket.on("new_notification", handleNewNotification);
  socket.on("notification:new", handleNewNotification);

  socket.on("notification:unread_count", (count: number) => {
    if (handlers.onUnreadCount) handlers.onUnreadCount(count);
  });

  socket.on("notification:read", (data: any) => {
    if (handlers.onRead) handlers.onRead(data);
  });

  return socket;
};

export const disconnectNotificationSocket = (socket: Socket | null): void => {
  if (socket) {
    socket.disconnect();
  }
};

// ─── Dispatch Event → Toast mapping ──────────────────────────────────

const DISPATCH_EVENT_CONFIG: Record<string, { type: 'success' | 'warning' | 'error' | 'info'; title: string; autoDismiss: number; priority: 'normal' | 'critical' }> = {
  'job.assigned': { type: 'info',    title: 'Job Assigned',   autoDismiss: 5000, priority: 'normal'   },
  'job.accepted': { type: 'success', title: 'Job Accepted',   autoDismiss: 5000, priority: 'normal'   },
  'job.rejected': { type: 'warning', title: 'Job Rejected',   autoDismiss: 8000, priority: 'critical' },
  'job.expired':  { type: 'error',   title: 'Job Expired',    autoDismiss: 10000,priority: 'critical' },
  'job.en_route': { type: 'info',    title: 'Tech En Route',  autoDismiss: 5000, priority: 'normal'   },
};

export const subscribeToDispatchEvents = (socket: Socket | null, onDispatchEvent: (toast: any) => void): (() => void) => {
  if (!socket) return () => {};

  const handlers: Record<string, (payload: any) => void> = {};

  Object.entries(DISPATCH_EVENT_CONFIG).forEach(([event, cfg]) => {
    const handler = (payload: any = {}) => {
      const jobTitle   = payload.job_title   || payload.title   || 'Unknown Job';
      const techName   = payload.tech_name   || payload.technician_name || '';
      const reason     = payload.reason      || '';
      const eta        = payload.eta         || '';

      let message = jobTitle;
      if (event === 'job.accepted' && techName)  message = `${techName} accepted ${jobTitle}`;
      if (event === 'job.rejected' && techName)  message = `${techName} rejected ${jobTitle}${reason ? ` — ${reason}` : ''}`;
      if (event === 'job.expired')               message = `${jobTitle} — Re-dispatching…`;
      if (event === 'job.en_route' && techName)  message = `${techName} is en route${eta ? ` — ETA ${eta}` : ''}`;
      if (event === 'job.assigned' && techName)  message = `${jobTitle} → ${techName}`;

      onDispatchEvent({
        type:       cfg.type,
        title:      cfg.title,
        message,
        jobId:      payload.job_id || payload.jobId,
        autoDismiss: cfg.autoDismiss,
        priority:   cfg.priority,
        eventType:  event,
      });
    };

    handlers[event] = handler;
    socket.on(event, handler);
  });

  // Return cleanup function
  return () => {
    Object.entries(handlers).forEach(([event, handler]) => {
      socket.off(event, handler);
    });
  };
};

export const createToastFromNotification = (notif: TechnicianNotification): any => {
  const typeMap = {
    JOB_ASSIGNED: { type: 'info' as const,    autoDismiss: 5000, priority: 'normal' as const,   eventType: 'job.assigned' as const },
    SLA_WARNING:  { type: 'warning' as const, autoDismiss: 8000, priority: 'critical' as const, eventType: undefined },
    JOB_UPDATED:  { type: 'info' as const,    autoDismiss: 5000, priority: 'normal' as const,   eventType: undefined },
    SYSTEM:       { type: 'info' as const,    autoDismiss: 5000, priority: 'normal' as const,   eventType: undefined },
  };
  const cfg = typeMap[notif.type] || typeMap.SYSTEM;
  return {
    type:       cfg.type,
    title:      notif.title || 'Notification',
    message:    notif.message || '',
    jobId:      notif.jobId,
    autoDismiss: cfg.autoDismiss,
    priority:   cfg.priority,
    eventType:  cfg.eventType,
  };
};
