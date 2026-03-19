import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Match, ApiResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class MatchService {
    private base = `${environment.apiUrl}/matches`;

    constructor(private http: HttpClient) { }

    getMatches(params: Record<string, string> = {}): Observable<ApiResponse<Match>> {
        return this.http.get<ApiResponse<Match>>(`${this.base}/`, { params });
    }

    getLiveMatches(): Observable<Match[]> {
        return this.http.get<Match[]>(`${this.base}/live/`);
    }

    getMatch(id: number): Observable<Match> {
        return this.http.get<Match>(`${this.base}/${id}/`);
    }
}
