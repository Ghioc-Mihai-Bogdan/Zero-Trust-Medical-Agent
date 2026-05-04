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

  // THE FIX: Advanced Client-Side Image Compression
  private async compressAndEncodeImage(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = (event: any) => {
        const img = new Image();
        img.src = event.target.result;
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');

          // Maximum dimensions for the vision model
          const MAX_WIDTH = 1024;
          const MAX_HEIGHT = 1024;
          let width = img.width;
          let height = img.height;

          // Calculate new dimensions while maintaining aspect ratio
          if (width > height) {
            if (width > MAX_WIDTH) {
              height *= MAX_WIDTH / width;
              width = MAX_WIDTH;
            }
          } else {
            if (height > MAX_HEIGHT) {
              width *= MAX_HEIGHT / height;
              height = MAX_HEIGHT;
            }
          }

          canvas.width = width;
          canvas.height = height;

          // Draw the resized image onto the canvas
          ctx?.drawImage(img, 0, 0, width, height);

          // CRITICAL: Force the output to be a compressed JPEG, even if they uploaded a PNG!
          const compressedBase64 = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
          resolve(compressedBase64);
        };
        img.onerror = error => reject(error);
      };
      reader.onerror = error => reject(error);
    });
  }

  async send() {
    if (!this.userInput.trim() && !this.selectedFile) return;

    let base64Image: string | undefined = undefined;

    // If an image file is attached, run it through the compression engine!
    if (this.selectedFile && this.selectedFile.type.startsWith('image/')) {
      try {
        base64Image = await this.compressAndEncodeImage(this.selectedFile);
      } catch (err) {
        console.error("Failed to compress and encode image", err);
      }
    }

    // Pass the extracted base64 string to your service
    this.chatService.sendMessage(this.userInput, this.selectedFile || undefined, base64Image);

    this.userInput = '';
    this.selectedFile = null;
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  }
}