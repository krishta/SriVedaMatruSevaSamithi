import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  /** In-memory only — never persisted to localStorage/sessionStorage (module 07). */
  private accessTokenSignal = signal<string | null>(null);
  private usernameSignal = signal<string | null>(null);

  constructor(private http: HttpClient) {}

  get accessToken(): string | null {
    return this.accessTokenSignal();
  }

  get isLoggedIn(): boolean {
    return !!this.accessTokenSignal();
  }

  get username(): string | null {
    return this.usernameSignal();
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(
        `${environment.apiBaseUrl}/auth/login`,
        { username, password },
        { withCredentials: true }
      )
      .pipe(
        tap((res) => {
          this.accessTokenSignal.set(res.access_token);
          this.usernameSignal.set(username);
        })
      );
  }

  logout(): void {
    this.accessTokenSignal.set(null);
    this.usernameSignal.set(null);
  }
}