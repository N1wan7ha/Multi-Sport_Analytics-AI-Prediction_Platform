import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-match-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Matches</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Matches page — coming in Phase 4.
        </p>
      </div>
    </div>
  `,
})
export class MatchListComponent {}
