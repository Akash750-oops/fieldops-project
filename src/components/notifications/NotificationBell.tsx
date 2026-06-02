import React, { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { motion } from "framer-motion";
import { NotificationBellProps } from "../../types/notifications.ts";
import "./notifications.css";

const playBeep = () => {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    const audioCtx = new AudioContextClass();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
    gainNode.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);

    oscillator.start();
    oscillator.stop(audioCtx.currentTime + 0.15);
  } catch (e) {
    console.warn("Web Audio Context blocked or unsupported:", e);
  }
};

export const NotificationBell: React.FC<NotificationBellProps> = ({
  unreadCount,
  onClick,
  isAnimated = true,
  showSound = true,
  className = ""
}) => {
  const prevCount = useRef(unreadCount);
  const [bounce, setBounce] = useState(false);

  useEffect(() => {
    if (unreadCount > prevCount.current) {
      if (isAnimated) {
        setBounce(true);
        const timer = setTimeout(() => setBounce(false), 500);
        return () => clearTimeout(timer);
      }
      if (showSound) {
        playBeep();
      }
    }
    prevCount.current = unreadCount;
  }, [unreadCount, isAnimated, showSound]);

  // Clean trigger for manual animation props
  useEffect(() => {
    if (isAnimated && unreadCount > 0) {
      setBounce(true);
      const timer = setTimeout(() => setBounce(false), 500);
      return () => clearTimeout(timer);
    }
  }, [isAnimated]);

  const displayCount = unreadCount > 99 ? "99+" : unreadCount;
  const hasUnread = unreadCount > 0;
  const ariaLabel = `Notifications, ${unreadCount} unread`;

  return (
    <div className={`noc-module ${className}`}>
      <button
        type="button"
        className={`notification-bell ${bounce ? "bell-bounce" : ""}`}
        onClick={onClick}
        aria-label={ariaLabel}
        title={ariaLabel}
      >
        <motion.div
          animate={bounce ? { rotate: [0, -15, 15, -15, 15, 0] } : {}}
          transition={{ duration: 0.5 }}
          style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <Bell size={20} />
        </motion.div>
        
        <span
          className={`notification-badge ${hasUnread ? "badge-red" : "badge-gray"}`}
          aria-hidden="true"
        >
          {displayCount}
        </span>
      </button>
    </div>
  );
};

export default NotificationBell;
