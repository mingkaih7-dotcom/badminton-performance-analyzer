import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="shell">
      <header class="top">
        <div class="brand">Badminton Performance Analyzer</div>
        <nav class="nav">
          <a routerLink="/upload" routerLinkActive="active">Upload</a>
          <a routerLink="/runs-list" routerLinkActive="active">Runs</a>
        </nav>
      </header>
      <main class="main">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [`
    .shell{font-family:system-ui,Segoe UI,Arial;min-height:100vh;background:#f6f7fb;color:#0f172a}
    .top{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e5e7eb;background:#ffffff;position:sticky;top:0;z-index:10}
    .brand{font-weight:800;letter-spacing:-0.01em}
    .nav{display:flex;align-items:center;gap:10px}
    .nav a{color:#475569;text-decoration:none;padding:8px 10px;border-radius:10px}
    .nav a:hover{background:#f1f5f9;color:#0f172a}
    .nav a.active{background:#e0e7ff;color:#1d4ed8}
    .main{padding:22px;max-width:1280px;margin:0 auto}
    @media (max-width: 720px){
      .main{padding:16px}
      .top{padding:12px 14px}
    }
  `]
})
export class AppComponent {}