import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, firstValueFrom } from 'rxjs';

export interface Message { role: 'user' | 'ai'; content: string; fileName?: string; }
export interface Session { id: string; title: string; }

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private apiUrl = '/api'; 

  sessions = new BehaviorSubject<Session[]>([]);
  activeSessionId = new BehaviorSubject<string | null>(null);
  currentChat = new BehaviorSubject<Message[]>([]);
  isLoading = new BehaviorSubject<boolean>(false);

  constructor() { 
    this.loadSessionsFromStorage(); 
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

  // --- THE FIX: Ghost Sessions ---
  // Notice we no longer push to this.sessions or localStorage here!
  startNewSession() {
    const newId = this.generateUUID();
    this.activeSessionId.next(newId);
    this.currentChat.next([{ role: 'ai', content: 'Hello, Doctor. How can the mesh assist you today?' }]);
  }

  async switchSession(id: string) {
    this.activeSessionId.next(id);
    this.currentChat.next([]); 
    try {
      const res: any = await firstValueFrom(this.http.get(`${this.apiUrl}/history?session_id=${id}`));
      if (res.history && res.history.length > 0) {
        const mapped: Message[] = res.history.map((msg: any) => ({
          role: msg.role === 'Clinical AI' ? 'ai' : 'user', content: msg.content
        }));
        this.currentChat.next(mapped);
      } else {
        this.currentChat.next([{ role: 'ai', content: 'Hello, Doctor. How can the mesh assist you today?' }]);
      }
    } catch (e) {
      this.currentChat.next([{ role: 'ai', content: 'Error loading history.' }]);
    }
  }

  deleteSession(id: string, event: Event) {
    event.stopPropagation(); 
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

  async sendMessage(prompt: string, file?: File) {
    const sessionId = this.activeSessionId.value;
    if (!sessionId) return; 

    // --- THE FIX: Lazy Saving ---
    // If the session doesn't exist in our list yet, create it NOW.
    const existingSession = this.sessions.value.find(s => s.id === sessionId);
    if (!existingSession) {
      const newTitle = prompt.substring(0, 25) + (prompt.length > 25 ? '...' : '');
      const newSession = { id: sessionId, title: newTitle };
      this.sessions.next([newSession, ...this.sessions.value]);
      localStorage.setItem('mesh_sessions', JSON.stringify(this.sessions.value));
    }

    this.currentChat.next([...this.currentChat.value, { role: 'user', content: prompt, fileName: file?.name }]);
    this.isLoading.next(true);

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('prompt', prompt);
    if (file) formData.append('file', file);

    try {
      const res: any = await firstValueFrom(this.http.post(`${this.apiUrl}/process`, formData));
      if (res.error) throw new Error(res.error);
      this.currentChat.next([...this.currentChat.value, { role: 'ai', content: res.natural_response }]);
    } catch (err: any) {
      console.error("RAW ERROR CAUGHT:", err);
      let errorMsg = "An unexpected error occurred.";
      if (err.error && err.error.error) errorMsg = err.error.error;
      else if (err.error && typeof err.error === 'string') errorMsg = `Server Error: ${err.error.substring(0, 50)}...`;
      else if (err.message) errorMsg = err.message;

      const lowerError = errorMsg.toLowerCase();
      if (lowerError.includes("429") || lowerError.includes("exhausted") || lowerError.includes("quota") || err.status === 500 || err.status === 502 || err.status === 503 || err.status === 504) {
         errorMsg = "The mesh is currently experiencing maximum capacity due to high traffic. Please wait 60 seconds.";
      } else {
         errorMsg = `System Error: ${errorMsg}`;
      }
      this.currentChat.next([...this.currentChat.value, { role: 'ai', content: errorMsg }]);
    } finally {
      this.isLoading.next(false);
    }
  }
}