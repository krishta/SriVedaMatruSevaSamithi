import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DonationReason {
  code: string;
  label: string;
  is_active: boolean;
  is_system: boolean;
}

@Injectable({ providedIn: 'root' })
export class DonationReasonService {
  private base = `${environment.apiBaseUrl}/donation-reasons`;

  constructor(private http: HttpClient) {}

  active(): Observable<DonationReason[]> {
    return this.http.get<DonationReason[]>(this.base);
  }

  all(): Observable<DonationReason[]> {
    return this.http.get<DonationReason[]>(`${this.base}/admin`);
  }

  create(label: string): Observable<DonationReason> {
    return this.http.post<DonationReason>(this.base, { label });
  }

  update(code: string, label: string): Observable<DonationReason> {
    return this.http.put<DonationReason>(`${this.base}/${encodeURIComponent(code)}`, { label });
  }

  archive(code: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${encodeURIComponent(code)}`);
  }

  activate(code: string): Observable<DonationReason> {
    return this.http.post<DonationReason>(`${this.base}/${encodeURIComponent(code)}/activate`, {});
  }
}
