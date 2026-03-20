import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { PredictionJob } from './api.service';

interface SocketHandlers {
  onPrediction: (job: PredictionJob) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: () => void;
}

@Injectable({
  providedIn: 'root',
})
export class LivePredictionSocketService {
  subscribeToMatch(matchId: number, handlers: SocketHandlers): () => void {
    const endpoint = this.buildSocketUrl(`/predictions/match/${matchId}/`);
    const socket = new WebSocket(endpoint);

    socket.onopen = () => {
      handlers.onOpen?.();
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(String(event.data));
        const job = this.extractPredictionJob(payload);
        if (job) {
          handlers.onPrediction(job);
        }
      } catch {
        // Ignore malformed frames from non-application messages.
      }
    };

    socket.onerror = () => {
      handlers.onError?.();
    };

    socket.onclose = () => {
      handlers.onClose?.();
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    };
  }

  private buildSocketUrl(pathSuffix: string): string {
    const base = environment.wsUrl;
    if (base.startsWith('ws://') || base.startsWith('wss://')) {
      return `${base}${pathSuffix}`;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${protocol}://${window.location.host}${base}${pathSuffix}`;
  }

  private extractPredictionJob(payload: unknown): PredictionJob | null {
    if (!payload || typeof payload !== 'object') {
      return null;
    }

    const typedPayload = payload as Record<string, unknown>;
    const directJob = typedPayload as unknown as PredictionJob;
    if (typeof directJob.id === 'number' && typeof directJob.match === 'number') {
      return directJob;
    }

    if (
      typedPayload['type'] === 'prediction.update'
      && typedPayload['data']
      && typeof typedPayload['data'] === 'object'
    ) {
      const inner = typedPayload['data'] as PredictionJob;
      if (typeof inner.id === 'number' && typeof inner.match === 'number') {
        return inner;
      }
    }

    return null;
  }
}
