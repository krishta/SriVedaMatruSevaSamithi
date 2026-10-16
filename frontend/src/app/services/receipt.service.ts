import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ReceiptLookupItem {
  receipt_no: string;
  amount_paise: number;
  reason: string;
  status: string;
  issued_at: string;
  pdf_url: string;
}

@Injectable({ providedIn: 'root' })
export class ReceiptService {
  private base = `${environment.apiBaseUrl}/receipts`;

  constructor(private http: HttpClient) {}

  lookup(phone: string, last4: string): Observable<ReceiptLookupItem[]> {
    return this.http.post<ReceiptLookupItem[]>(`${this.base}/lookup`, { phone, last4 });
  }

  void(receiptId: number, reason: string): Observable<unknown> {
    return this.http.post(`${this.base}/${receiptId}/void`, { reason });
  }

  reissue(receiptId: number): Observable<unknown> {
    return this.http.post(`${this.base}/${receiptId}/reissue`, {});
  }

  pdfUrl(receiptId: number): string {
    return `${this.base}/${receiptId}/pdf`;
  }
}