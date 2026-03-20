import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AdminUser } from '../../../core/models';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h3>User Management</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Manage user roles and status.</p>

      <div *ngIf="loading" class="text-secondary">Loading users...</div>
      <div *ngIf="error" style="color:#d83a52;">{{ error }}</div>

      <div *ngIf="!loading && users.length > 0" style="margin-top:1rem;">
        <table style="width:100%; border-collapse:collapse;">
          <thead style="border-bottom:1px solid #ddd;">
            <tr style="text-align:left; font-weight:bold;">
              <th style="padding:.5rem;">Email</th>
              <th style="padding:.5rem;">Username</th>
              <th style="padding:.5rem;">Role</th>
              <th style="padding:.5rem;">Status</th>
              <th style="padding:.5rem;">Joined</th>
              <th style="padding:.5rem;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let user of users" style="border-bottom:1px solid #eee;">
              <td style="padding:.5rem;">{{ user.email }}</td>
              <td style="padding:.5rem;">{{ user.username }}</td>
              <td style="padding:.5rem;">
                <span [style.color]="user.role === 'ADMIN' ? '#d84315' : '#1976d2'">
                  {{ user.role }}
                </span>
              </td>
              <td style="padding:.5rem;">
                <span [style.color]="user.is_active ? '#388e3c' : '#c62828'">
                  {{ user.is_active ? '✓ Active' : '✗ Disabled' }}
                </span>
              </td>
              <td style="padding:.5rem; font-size:0.85rem;">{{ user.date_joined | date:'short' }}</td>
              <td style="padding:.5rem;">
                <button
                  (click)="toggleUserStatus(user)"
                  class="btn"
                  [disabled]="toggling[user.id]"
                  [style.backgroundColor]="user.is_active ? '#c62828' : '#388e3c'"
                  [style.color]="'white'"
                  [style.opacity]="toggling[user.id] ? '0.6' : '1.0'"
                  style="padding:0.25rem 0.5rem; font-size:0.85rem; cursor:pointer; border:none; border-radius:3px; transition:all 0.2s;"
                >
                  {{ user.is_active ? 'Disable' : 'Enable' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div *ngIf="!loading && users.length === 0" class="text-secondary">
        No users found.
      </div>
    </div>
  `,
})
export class AdminUsersComponent implements OnInit {
  users: AdminUser[] = [];
  loading = false;
  error = '';
  toggling: { [key: number]: boolean } = {};

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  private loadUsers(): void {
    this.loading = true;
    this.error = '';
    const apiUrl = `${environment.apiUrl}/admin/users/`;

    this.http.get<AdminUser[]>(apiUrl).subscribe({
      next: (response) => {
        this.users = Array.isArray(response) ? response : (response as any).results || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load users';
      },
    });
  }

  toggleUserStatus(user: AdminUser): void {
    this.toggling[user.id] = true;
    const action = user.is_active ? 'disable_user' : 'enable_user';
    const url = `${environment.apiUrl}/admin/users/${user.id}/${action}/`;

    this.http.post<AdminUser>(url, {}).subscribe({
      next: (updatedUser) => {
        user.is_active = updatedUser.is_active;
        this.toggling[user.id] = false;
      },
      error: () => {
        this.error = 'Failed to update user status';
        this.toggling[user.id] = false;
      },
    });
  }
}
