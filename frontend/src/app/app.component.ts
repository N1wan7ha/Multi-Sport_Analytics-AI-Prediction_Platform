import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule],
  template: `
    <div class="app-shell">
      <!-- Sidebar will be added in Phase 4 -->
      <main class="main-content" style="margin-left:0; padding-top:0;">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class AppComponent {
  title = 'MatchMind — Multi-Sport Prediction Platform';
}
