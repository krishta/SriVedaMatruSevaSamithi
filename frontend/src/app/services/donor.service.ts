import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DonorDonationItem {
  id: number;
  amount_paise: number;
  reason: string;
  status: string;
  receipt_no: string | null;
  created_at: string;
}

export interface DonorDetail {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  lifetime_total_paise: number;
  donations: DonorDonationItem[];
}

export interface DonorListItem {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  created_at: string;
}

export interface DonorListResponse {
  items: DonorListItem[];
  total: number;
  page: number;
  size: number;
}

export interface DonorPayload {
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
}

@Injectable({ providedIn: 'root' })
export class DonorService {
  private base = `${environment.apiBaseUrl}/donors`;

  constructor(private http: HttpClient) {}

  list(params: Record<string, string | number> = {}): Observable<DonorListResponse> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get<DonorListResponse>(query ? `${this.base}?${query}` : this.base);
  }

  get(donorId: number): Observable<DonorDetail> {
    return this.http.get<DonorDetail>(`${this.base}/${donorId}`);
  }

  create(payload: DonorPayload): Observable<DonorListItem> {
    return this.http.post<DonorListItem>(this.base, payload);
  }

  update(donorId: number, payload: DonorPayload): Observable<DonorListItem> {
    return this.http.put<DonorListItem>(`${this.base}/${donorId}`, payload);
  }

  delete(donorId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${donorId}`);
  }
}