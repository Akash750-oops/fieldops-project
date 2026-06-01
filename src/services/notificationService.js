import axios from "axios";
import { io } from "socket.io-client";

const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer mock-token",
    "X-Tenant-ID": "tenant-1"
  }
});

// Mock notification database when server is not available or for demo
let mockNotifications = [
  {
    id: "notif-1",
    type: "JOB_ASSIGNED",
    title: "New Job Assigned",
    message: "AC repair job assigned near Anna Nagar",
    isRead: false,
    createdAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    jobId: 101,
    job: {
      id: 101,
      title: "AC Repair Service",
      description: "Customer reported cooling issue in split AC.",
      location: "Anna Nagar, Chennai",
      priority: "HIGH",
      customer_name: "Arun Kumar",
      customer_phone: "+91 9876543210",
      estimated_value: 2500,
      sla_deadline: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      distance_km: 6.8,
      required_skills: ["AC Repair", "Electrical", "Customer Support"]
    }
  },
  {
    id: "notif-2",
    type: "SLA_WARNING",
    title: "SLA Warning",
    message: "AC Repair Service SLA deadline is in 15 minutes!",
    isRead: false,
    createdAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    jobId: 101,
    job: {
      id: 101,
      title: "AC Repair Service",
      description: "Customer reported cooling issue in split AC.",
      location: "Anna Nagar, Chennai",
      priority: "HIGH",
      customer_name: "Arun Kumar",
      customer_phone: "+91 9876543210",
      estimated_value: 2500,
      sla_deadline: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      distance_km: 6.8,
      required_skills: ["AC Repair", "Electrical", "Customer Support"]
    }
  }
];

export const fetchNotifications = async (techId) => {
  try {
    const response = await api.get(`/technicians/${techId}/notifications`);
    const notifications = response.data.notifications.map(n => ({
      id: n.id,
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
    console.warn("Failed to fetch notifications from backend, using mock data", error);
    const unreadCount = mockNotifications.filter(n => !n.isRead).length;
    return {
      notifications: [...mockNotifications],
      unreadCount,
      total: mockNotifications.length
    };
  }
};

export const fetchUnreadCount = async (techId) => {
  try {
    const data = await fetchNotifications(techId);
    return data.unreadCount;
  } catch (error) {
    return mockNotifications.filter(n => !n.isRead).length;
  }
};

export const markNotificationAsRead = async (notificationId) => {
  try {
    if (String(notificationId).startsWith("notif-")) {
      mockNotifications = mockNotifications.map(n =>
        n.id === notificationId ? { ...n, isRead: true } : n
      );
      return { success: true };
    }
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
  } catch (error) {
    console.warn("Failed to mark read on backend, updating mock data", error);
    mockNotifications = mockNotifications.map(n =>
      n.id === notificationId ? { ...n, isRead: true } : n
    );
    return { success: true };
  }
};

export const registerFCMToken = async (techId, token) => {
  try {
    const response = await api.post(`/technicians/${techId}/fcm-token`, {
      token,
      device_type: "web"
    });
    return response.data;
  } catch (error) {
    console.warn("Failed to register FCM token with backend", error);
    return { status: "registered_mock" };
  }
};

export const connectNotificationSocket = (tokenOrTechnicianId, handlers = {}) => {
  const techId = tokenOrTechnicianId;
  const socket = io(BASE_URL, {
    query: { tech_id: techId },
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 2000,
    transports: ["websocket", "polling"]
  });

  socket.on("connect", () => {
    console.log("Socket connected, room technician:", techId);
    if (handlers.onConnect) handlers.onConnect();
  });

  socket.on("disconnect", (reason) => {
    console.log("Socket disconnected:", reason);
    if (handlers.onDisconnect) handlers.onDisconnect(reason);
  });

  const handleNewNotification = (payload) => {
    console.log("Real-time notification payload received:", payload);
    const formatted = {
      id: payload.id || `notif-${Date.now()}`,
      type: payload.type || "SYSTEM",
      title: payload.title || "Alert",
      message: payload.body || payload.message || "",
      isRead: false,
      createdAt: payload.created_at || new Date().toISOString(),
      jobId: payload.job_id || payload.jobId,
      job: payload.job || payload.notification_metadata?.job || null
    };

    if (!mockNotifications.some(n => n.id === formatted.id)) {
      mockNotifications = [formatted, ...mockNotifications];
    }

    if (handlers.onNewNotification) {
      handlers.onNewNotification(formatted);
    }
  };

  socket.on("new_notification", handleNewNotification);
  socket.on("notification:new", handleNewNotification);

  socket.on("notification:unread_count", (count) => {
    if (handlers.onUnreadCount) handlers.onUnreadCount(count);
  });

  socket.on("notification:read", (data) => {
    if (handlers.onRead) handlers.onRead(data);
  });

  return socket;
};

export const disconnectNotificationSocket = (socket) => {
  if (socket) {
    socket.disconnect();
  }
};
