import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface NgoSettingsPublic {
  name: string;
  address: string;
  upi_id: string;
  bank_details: { account_name?: string; account_no?: string; ifsc?: string; bank?: string };
  logo_url: string | null;
}

export interface NgoSettingsAdmin extends NgoSettingsPublic {
  reg_80g_number: string | null;
}

export interface NgoSettingsUpdatePayload {
  name: string;
  address: string;
  upi_id: string;
  bank_details: { account_name?: string; account_no?: string; ifsc?: string; bank?: string };
  reg_80g_number: string | null;
}

/** Prefixes a backend-relative URL (e.g. /api/ngo-settings/logo) with the API origin. */
export function toAbsoluteApiUrl(relativeUrl: string): string {
  const origin = environment.apiBaseUrl.replace(/\/api$/, '');
  return `${origin}${relativeUrl}`;
}

@Injectable({ providedIn: 'root' })
export class NgoSettingsService {
  constructor(private http: HttpClient) {}

  getPublic(): Observable<NgoSettingsPublic> {
    return this.http.get<NgoSettingsPublic>(`${environment.apiBaseUrl}/ngo-settings/public`);
  }

  getAdmin(): Observable<NgoSettingsAdmin> {
    return this.http.get<NgoSettingsAdmin>(`${environment.apiBaseUrl}/ngo-settings`);
  }

  update(payload: NgoSettingsUpdatePayload): Observable<NgoSettingsAdmin> {
    return this.http.put<NgoSettingsAdmin>(`${environment.apiBaseUrl}/ngo-settings`, payload);
  }
}