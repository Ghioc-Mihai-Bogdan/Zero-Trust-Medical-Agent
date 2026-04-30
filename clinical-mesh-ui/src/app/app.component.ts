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

  // NEW: Helper function to extract base64 from the image file
  private async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        // e.target.result looks like "data:image/jpeg;base64,/9j/4..."
        // We MUST split at the comma and only send the raw string!
        const base64String = (reader.result as string).split(',')[1];
        resolve(base64String);
      };
      reader.onerror = error => reject(error);
    });
  }

  // NEW: Made async so we can await the base64 encoding before sending
  async send() {
    if (!this.userInput.trim() && !this.selectedFile) return;

    let base64Image: string | undefined = undefined;

    // If an image file is attached, encode it!
    if (this.selectedFile && this.selectedFile.type.startsWith('image/')) {
      try {
        base64Image = await this.fileToBase64(this.selectedFile);
      } catch (err) {
        console.error("Failed to encode image", err);
      }
    }

    // Pass the extracted base64 string to your service
    // (We pass it as a third parameter so we don't break existing file logic)
    this.chatService.sendMessage(this.userInput, this.selectedFile || undefined, base64Image);

    this.userInput = '';
    this.selectedFile = null;
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  }
}