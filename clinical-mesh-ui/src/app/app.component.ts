import { Component, inject, ViewChild, ElementRef, AfterViewChecked, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from './services/chat.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements AfterViewChecked, OnInit {
  chatService = inject(ChatService);
  userInput = '';
  selectedFile: File | null = null;
  isDarkTheme = true;

  @ViewChild('chatBox') private chatBoxRef!: ElementRef;

  ngOnInit() {
    const savedTheme = localStorage.getItem('mesh_theme');
    if (savedTheme === 'light') {
      this.isDarkTheme = false;
    }
  }

  toggleTheme() {
    this.isDarkTheme = !this.isDarkTheme;
    localStorage.setItem('mesh_theme', this.isDarkTheme ? 'dark' : 'light');
  }

  ngAfterViewChecked() { this.scrollToBottom(); }
  scrollToBottom(): void { try { this.chatBoxRef.nativeElement.scrollTop = this.chatBoxRef.nativeElement.scrollHeight; } catch(err) { } }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) { 
      this.selectedFile = file; 
      // The annoying browser alert is officially deleted!
    }
  }

  removeFile() {
    this.selectedFile = null;
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  }

  handleEnter(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); this.send(); }
  }

  send() {
    if (!this.userInput.trim() && !this.selectedFile) return;
    this.chatService.sendMessage(this.userInput, this.selectedFile || undefined);
    this.userInput = '';
    this.selectedFile = null;
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  }
}