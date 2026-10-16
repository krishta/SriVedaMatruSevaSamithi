import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface MeetingListItem {
  id: number;
  meeting_date: string;
  notes_preview: string;
  created_at: string;
  updated_at: string;
}

export interface MeetingListResponse {
  items: MeetingListItem[];
  total: number;
  page: number;
  size: number;
}

export interface MeetingDetail {
  id: number;
  meeting_date: string;
  notes_html: string;
  created_at: string;
  updated_at: string;
}

export interface MeetingPayload {
  meeting_date: string;
  notes_html: string;
}

@Injectable({ providedIn: 'root' })
export class MeetingService {
  private base = `${environment.apiBaseUrl}/meetings`;

  constructor(private http: HttpClient) {}

  list(params: Record<string, string | number> = {}): Observable<MeetingListResponse> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get<MeetingListResponse>(query ? `${this.base}?${query}` : this.base);
  }

  get(meetingId: number): Observable<MeetingDetail> {
    return this.http.get<MeetingDetail>(`${this.base}/${meetingId}`);
  }

  create(payload: MeetingPayload): Observable<MeetingDetail> {
    return this.http.post<MeetingDetail>(this.base, payload);
  }

  update(meetingId: number, payload: MeetingPayload): Observable<MeetingDetail> {
    return this.http.put<MeetingDetail>(`${this.base}/${meetingId}`, payload);
  }

  delete(meetingId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${meetingId}`);
  }

  exportOne(meetingId: number): Observable<Blob> {
    return this.http.get(`${this.base}/${meetingId}/export`, { responseType: 'blob' });
  }

  exportAll(params: Record<string, string | number> = {}): Observable<Blob> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get(query ? `${this.base}/export?${query}` : `${this.base}/export`, {
      responseType: 'blob',
    });
  }
}