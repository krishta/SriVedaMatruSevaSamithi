import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DonationReportRequest {
  report_type: string;
  columns: string[];
  date_from: string | null;
  date_to: string | null;
  reason_code: string | null;
  include_voided: boolean;
}

@Injectable({ providedIn: 'root' })
export class ReportService {
  private base = `${environment.apiBaseUrl}/reports`;

  constructor(private http: HttpClient) {}

  export(payload: DonationReportRequest): Observable<Blob> {
    return this.http.post(`${this.base}/export`, payload, { responseType: 'blob' });
  }
}
