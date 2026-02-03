import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  message: string;
  duration?: number;
  dismissible?: boolean;
}

/**
 * Notification Service
 * 
 * Manages application-wide notifications.
 * Provides a centralized way to show toast notifications.
 */
@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private readonly notificationsSubject = new BehaviorSubject<Notification[]>([]);
  readonly notifications$: Observable<Notification[]> = this.notificationsSubject.asObservable();
  
  private readonly DEFAULT_DURATION = 5000;
  
  /**
   * Shows a notification
   */
  show(notification: Omit<Notification, 'id'>): string {
    const id = this.generateId();
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? this.DEFAULT_DURATION,
      dismissible: notification.dismissible ?? true
    };
    
    this.notificationsSubject.next([...this.notificationsSubject.value, newNotification]);
    
    // Auto-dismiss after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => this.dismiss(id), newNotification.duration);
    }
    
    return id;
  }
  
  /**
   * Shows an info notification
   */
  info(message: string, title?: string): string {
    return this.show({ type: 'info', message, title });
  }
  
  /**
   * Shows a success notification
   */
  success(message: string, title?: string): string {
    return this.show({ type: 'success', message, title });
  }
  
  /**
   * Shows a warning notification
   */
  warning(message: string, title?: string): string {
    return this.show({ type: 'warning', message, title });
  }
  
  /**
   * Shows an error notification
   */
  error(message: string, title?: string): string {
    return this.show({ type: 'error', message, title, duration: 0 });
  }
  
  /**
   * Dismisses a notification by ID
   */
  dismiss(id: string): void {
    this.notificationsSubject.next(
      this.notificationsSubject.value.filter(n => n.id !== id)
    );
  }
  
  /**
   * Clears all notifications
   */
  clear(): void {
    this.notificationsSubject.next([]);
  }
  
  private generateId(): string {
    return `notif_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  }
}
