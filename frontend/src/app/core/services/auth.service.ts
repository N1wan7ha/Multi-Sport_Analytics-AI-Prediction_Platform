import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthTokens, User } from '../models';

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

    loadProfile(): Observable<User> {
        return this.http.get<User>(`${this.base}/profile/`).pipe(
            tap(user => this._currentUser.next(user))
        );
    }
}
