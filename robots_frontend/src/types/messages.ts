export interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'video' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
}