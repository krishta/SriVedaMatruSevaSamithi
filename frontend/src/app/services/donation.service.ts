import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DonationCreateResponse {
  donation_id: number;
  donor_id: number;
  receipt_no: string;
  pdf_url: string;
  email_sent: boolean;
}

export interface DonationListResponse {
  items: Array<{
    id: number;
    donor_id: number;
    donor_name: string;
    donor_phone: string;
    amount_paise: number;
    reason: string;
    reason_other: string | null;
    mode: string;
    status: string;
    receipt_id: number | null;
    receipt_no: string | null;
    created_at: string;
  }>;
  total: number;
  page: number;
  size: number;
}

export interface BatchReceiptResultItem {
  donor_id: number;
  donor_name: string;
  status: 'generated' | 'failed';
  receipt_no: string | null;
  receipt_id: number | null;
  pdf_url: string | null;
  email_sent: boolean;
  error: string | null;
}

export interface BatchReceiptResponse {
  period: string;
  generated: number;
  failed: number;
  results: BatchReceiptResultItem[];
}

@Injectable({ providedIn: 'root' })
export class DonationService {
  private base = `${environment.apiBaseUrl}/donations`;

  constructor(private http: HttpClient) {}

  submit(formData: FormData): Observable<DonationCreateResponse> {
    return this.http.post<DonationCreateResponse>(this.base, formData);
  }

  generateBatch(formData: FormData): Observable<BatchReceiptResponse> {
    return this.http.post<BatchReceiptResponse>(`${this.base}/batch`, formData);
  }

  list(params: Record<string, string | number>): Observable<DonationListResponse> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get<DonationListResponse>(`${this.base}?${query}`);
  }

  /** Blob response so the auth interceptor's Authorization header actually applies — a plain
   * `<a href>` navigation bypasses HttpClient entirely and hits the API unauthenticated. */
  exportCsv(params: Record<string, string | number> = {}): Observable<Blob> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get(`${this.base}/export${query ? '?' + query : ''}`, { responseType: 'blob' });
  }
}