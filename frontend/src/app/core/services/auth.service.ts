import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthTokens, User } from '../models';

export interface TeamOption {
    id: number;
    name: string;
    short_name?: string;
}

export interface PredictionHistoryEntry {
    id: number;
    match: number;
    match_name: string;
    prediction_type: string;
    status: string;
    model_version: string;
    requested_at: string;
    completed_at?: string | null;
    result?: {
        team1_win_probability: number;
        team2_win_probability: number;
        confidence_score: number;
        current_over?: number | null;
        current_score?: string;
    } | null;
}

export interface PaginatedResponse<T> {
    count: number;
    results: T[];
}

@Injectable({ providedIn: 'root' })
export class AuthService {
    private base = `${environment.apiUrl}/auth`;
    private _currentUser = new BehaviorSubject<User | null>(null);

    currentUser$ = this._currentUser.asObservable();

    constructor(private http: HttpClient) {
        // Restore user from localStorage on init
        const token = this.getAccessToken();
        if (token) this.loadProfile().subscribe();
    }

    login(email: string, password: string): Observable<AuthTokens> {
        return this.http.post<AuthTokens>(`${this.base}/login/`, { email, password }).pipe(
            tap(tokens => {
                localStorage.setItem('access_token', tokens.access);
                localStorage.setItem('refresh_token', tokens.refresh);
                this.loadProfile().subscribe();
            })
        );
    }

    googleLogin(token: string): Observable<AuthTokens> {
        return this.http.post<AuthTokens>(`${this.base}/google/`, { token }).pipe(
            tap(tokens => {
                localStorage.setItem('access_token', tokens.access);
                localStorage.setItem('refresh_token', tokens.refresh);
                this.loadProfile().subscribe();
            })
        );
    }

    register(email: string, username: string, password: string): Observable<User> {
        return this.http.post<User>(`${this.base}/register/`, { email, username, password });
    }

    logout(): void {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this._currentUser.next(null);
    }

    getAccessToken(): string | null {
        return localStorage.getItem('access_token');
    }

    isLoggedIn(): boolean {
        return !!this.getAccessToken();
    }

    getCurrentUserRole(): 'ADMIN' | 'USER' | null {
        const token = this.getAccessToken();
        if (!token) {
            return null;
        }

        const payload = this.decodeJwtPayload(token);
        const role = payload?.['role'];
        return role === 'ADMIN' || role === 'USER' ? role : null;
    }

    private decodeJwtPayload(token: string): Record<string, unknown> | null {
        try {
            const parts = token.split('.');
            if (parts.length !== 3) {
                return null;
            }

            const payloadSegment = parts[1]
                .replace(/-/g, '+')
                .replace(/_/g, '/');
            const normalized = payloadSegment + '='.repeat((4 - (payloadSegment.length % 4)) % 4);
            return JSON.parse(atob(normalized));
        } catch {
            return null;
        }
    }

    loadProfile(): Observable<User> {
        return this.http.get<User>(`${this.base}/profile/`).pipe(
            tap(user => this._currentUser.next(user))
        );
    }

    updateProfile(payload: { bio?: string; favourite_team_ids?: number[]; favourite_team?: string }): Observable<User> {
        return this.http.patch<User>(`${this.base}/profile/`, payload).pipe(
            tap(user => this._currentUser.next(user))
        );
    }

    getTeamOptions(): Observable<TeamOption[]> {
        return this.http.get<TeamOption[]>(`${this.base}/team-options/`);
    }

    getPredictionHistory(): Observable<PaginatedResponse<PredictionHistoryEntry>> {
        return this.http.get<PaginatedResponse<PredictionHistoryEntry>>(`${this.base}/prediction-history/`);
    }

    resendEmailVerification(): Observable<{ detail: string }> {
        return this.http.post<{ detail: string }>(`${this.base}/verify-email/`, {});
    }

    confirmEmailVerification(token: string): Observable<{ detail: string }> {
        return this.http.post<{ detail: string }>(`${this.base}/verify-email/confirm/`, { token });
    }
}
