import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subscription, firstValueFrom } from 'rxjs';

export interface Message { role: 'user' | 'ai'; content: string; fileName?: string; }
export interface Session { id: string; title: string; }

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private apiUrl = '/api'; 
  
  private pendingRequests = new Map<string, Subscription>();
  private loadingMap = new Set<string>();

  sessions = new BehaviorSubject<Session[]>([]);
  activeSessionId = new BehaviorSubject<string | null>(null);
  currentChat = new BehaviorSubject<Message[]>([]);
  isLoading = new BehaviorSubject<boolean>(false);

  constructor() { 
    this.loadSessionsFromStorage(); 
  }

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
      req.unsubscribe(); 
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
    this.activeSessionId.next(id);
    this.updateLoadingState();
    this.currentChat.next([]); 
    
    try {
      const res: any = await firstValueFrom(this.http.get(`${this.apiUrl}/history?session_id=${id}`));
      const welcomeMsg: Message = { role: 'ai', content: 'Hello, Doctor. How can the mesh assist you today?' };
      
      if (res.history && res.history.length > 0) {
        const mapped: Message[] = res.history.map((msg: any) => ({
          role: msg.role === 'Clinical AI' ? 'ai' : 'user', 
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
    this.stopGeneration(); 
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

  // FIXED: Added base64Image to the expected arguments!
  sendMessage(prompt: string, file?: File, base64Image?: string) {
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
    
    this.loadingMap.add(sessionId);
    this.updateLoadingState();

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('prompt', prompt);
    
    // THE FIX: Strict Routing with a Safety Net
    if (base64Image) {
      // Success: Send the lightweight compressed string
      formData.append('base64_image', base64Image);
      if (file) formData.append('image_name', file.name); 

      // === DIAGNOSTIC LOG ===
      // This will print the exact size of the compressed base64 string in Kilobytes
      console.log("Diagnostic - Payload Size (KB):", Math.round(base64Image.length / 1024));
      // ======================

    } else if (file) {
      // DANGER CHECK: Is it an image that failed compression?
      if (file.type.startsWith('image/')) {
         console.error("CRITICAL: Image compression failed. Aborting upload to prevent network crash.");
         
         // Cleanly reset the UI state
         this.loadingMap.delete(sessionId);
         this.pendingRequests.delete(sessionId);
         this.updateLoadingState();
         
         // Display a graceful error message in the chat
         this.currentChat.next([...this.currentChat.value, { 
           role: 'ai', 
           content: '🛑 System Error: The image was too massive for the browser to compress, or the format is corrupted. Please try a smaller file.' 
         }]);
         return; // STOP THE REQUEST!
      }
      
      // It's a text/PDF document: Send the actual binary file safely
      formData.append('file', file);
    }

    const req = this.http.post(`${this.apiUrl}/process`, formData).subscribe({
      next: (res: any) => {
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
         this.currentChat.next([...this.currentChat.value, { role: 'ai', content: '🛑 Network Error: The server dropped the connection.' }]);
      }
    });
    
    this.pendingRequests.set(sessionId, req);
  }
}