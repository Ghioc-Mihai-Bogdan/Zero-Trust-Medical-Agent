import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subscription, firstValueFrom } from 'rxjs';

export interface Message { role: 'user' | 'ai'; content: string; fileName?: string; }
export interface Session { id: string; title: string; }

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private apiUrl = '/api'; 
  
  // FIX: Maps to track background generations per-session
  private pendingRequests = new Map<string, Subscription>();
  private loadingMap = new Set<string>();

  sessions = new BehaviorSubject<Session[]>([]);
  activeSessionId = new BehaviorSubject<string | null>(null);
  currentChat = new BehaviorSubject<Message[]>([]);
  isLoading = new BehaviorSubject<boolean>(false);

  constructor() { 
    this.loadSessionsFromStorage(); 
  }

  // Refreshes the UI loading state based on which chat you are currently viewing
  private updateLoadingState() {
    this.isLoading.next(this.loadingMap.has(this.activeSessionId.value || ''));
  }

  private loadSessionsFromStorage() {
    const saved = localStorage.getItem('mesh_sessions');
    if (saved && saved !== '[]') {
      const parsed = JSON.parse(saved);
      this.sessions.next(parsed);
      if (parsed.length > 0) {
        this.switchSession(parsed[0].id);
        return; 
      }
    }
    this.startNewSession();
  }

  private generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  stopGeneration() {
    const sessionId = this.activeSessionId.value;
    if (!sessionId) return;
    const req = this.pendingRequests.get(sessionId);
    if (req) {
      req.unsubscribe(); // Severs the HTTP connection
      this.pendingRequests.delete(sessionId);
      this.loadingMap.delete(sessionId);
      this.updateLoadingState();
      this.currentChat.next([...this.currentChat.value, { role: 'ai', content: '🛑 Generation cancelled by user.' }]);
    }
  }

  startNewSession() {
    const newId = this.generateUUID();
    this.activeSessionId.next(newId);
    this.updateLoadingState();
    this.currentChat.next([{ role: 'ai', content: 'Hello, Doctor. How can the mesh assist you today?' }]);
  }

  async switchSession(id: string) {
    // We NO LONGER call stopGeneration() here! The old chat will keep generating safely in the background.
    this.activeSessionId.next(id);
    this.updateLoadingState();
    this.currentChat.next([]); 
    
    try {
      const res: any = await firstValueFrom(this.http.get(`${this.apiUrl}/history?session_id=${id}`));
      const welcomeMsg: Message = { role: 'ai', content: 'Hello, Doctor. How can the mesh assist you today?' };
      
      if (res.history && res.history.length > 0) {
        const mapped: Message[] = res.history.map((msg: any) => ({
          role: msg.role === 'Clinical AI' ? 'ai' : 'user', 
          // FIX: Force empty strings if null to prevent the bubble from disappearing
          content: msg.content || '', 
          fileName: msg.file_name || msg.fileName
        }));
        this.currentChat.next([welcomeMsg, ...mapped]);
      } else {
        this.currentChat.next([welcomeMsg]);
      }
    } catch (e) {
      this.currentChat.next([{ role: 'ai', content: 'Error loading history.' }]);
    }
  }

  deleteSession(id: string, event: Event) {
    event.stopPropagation(); 
    this.stopGeneration(); // Stop if deleted
    const updatedSessions = this.sessions.value.filter(s => s.id !== id);
    this.sessions.next(updatedSessions);
    localStorage.setItem('mesh_sessions', JSON.stringify(updatedSessions));
    
    if (this.activeSessionId.value === id) {
      if (updatedSessions.length > 0) {
        this.switchSession(updatedSessions[0].id);
      } else {
        this.startNewSession();
      }
    }
  }

  sendMessage(prompt: string, file?: File) {
    const sessionId = this.activeSessionId.value;
    if (!sessionId) return; 

    const existingSession = this.sessions.value.find(s => s.id === sessionId);
    if (!existingSession) {
      const newTitle = prompt.substring(0, 25) + (prompt.length > 25 ? '...' : '');
      const newSession = { id: sessionId, title: newTitle };
      this.sessions.next([newSession, ...this.sessions.value]);
      localStorage.setItem('mesh_sessions', JSON.stringify(this.sessions.value));
    }

    this.currentChat.next([...this.currentChat.value, { role: 'user', content: prompt, fileName: file?.name }]);
    
    // Track loading for THIS specific session
    this.loadingMap.add(sessionId);
    this.updateLoadingState();

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('prompt', prompt);
    if (file) formData.append('file', file);

    const req = this.http.post(`${this.apiUrl}/process`, formData).subscribe({
      next: (res: any) => {
        // --- NEW FEATURE: Dynamically update the sidebar title ---
        if (res.session_title) {
          const sessions = this.sessions.value;
          const s = sessions.find(s => s.id === sessionId);
          if (s) {
            s.title = res.session_title;
            this.sessions.next([...sessions]);
            localStorage.setItem('mesh_sessions', JSON.stringify(sessions));
          }
        }

        if (this.activeSessionId.value === sessionId) {
          if (res.error) this.currentChat.next([...this.currentChat.value, { role: 'ai', content: res.error }]);
          else this.currentChat.next([...this.currentChat.value, { role: 'ai', content: res.natural_response }]);
        }
        this.loadingMap.delete(sessionId);
        this.pendingRequests.delete(sessionId);
        this.updateLoadingState();
      },
      error: (err: any) => {
         console.error("RAW ERROR CAUGHT:", err);
         this.loadingMap.delete(sessionId);
         this.pendingRequests.delete(sessionId);
         this.updateLoadingState();
      }
    });
    
    this.pendingRequests.set(sessionId, req);
  }
}