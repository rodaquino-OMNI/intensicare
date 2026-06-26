// API client with JWT auth
import type { TokenResponse, LoginRequest } from '../types';

const API_BASE = '/api/v1';
const AUTH_BASE = '/auth';

class ApiClient {
  private token: string | null = null;

  constructor() {
    const stored = sessionStorage.getItem('access_token');
    if (stored) {
      this.token = stored;
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      sessionStorage.setItem('access_token', token);
    } else {
      sessionStorage.removeItem('access_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  isAuthenticated(): boolean {
    return this.token !== null;
  }

  private async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.setToken(null);
      throw new Error('Authentication required');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const result = await this.request<TokenResponse>(`${AUTH_BASE}/login`, {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    this.setToken(result.access_token);
    return result;
  }

  logout() {
    this.setToken(null);
  }

  // Dashboard
  async getDashboard(unit?: string) {
    const params = unit ? `?unit=${encodeURIComponent(unit)}` : '';
    return this.request<any>(`${API_BASE}/dashboard${params}`);
  }

  // Patient detail
  async getPatientDetail(mpiId: string) {
    return this.request<any>(`${API_BASE}/patients/${encodeURIComponent(mpiId)}/detail`);
  }

  // Alerts
  async getAlerts(params?: { status?: string; mpi_id?: string; limit?: number; offset?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.mpi_id) searchParams.set('mpi_id', params.mpi_id);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const qs = searchParams.toString();
    return this.request<any>(`${API_BASE}/alerts${qs ? '?' + qs : ''}`);
  }

  async acknowledgeAlert(alertId: number, notes?: string) {
    return this.request<any>(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ notes: notes || null }),
    });
  }
}

export const apiClient = new ApiClient();
